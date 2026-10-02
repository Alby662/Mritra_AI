"""IBM Graph Feature Preprocessor (GFP) wrapper (plan §7.1).

Wraps ``snapml.GraphFeaturePreprocessor`` to produce edge-level graph features
(fan-in/out, degree, scatter-gather, temporal-cycle, etc.) from the AMLworld
transaction table.  Falls back to a minimal NetworkX stub when snapml is not
installed (e.g. on macOS or Windows) so the rest of the pipeline can still run.

Streaming / no-future-leakage (CLAUDE.md §4, §6)
-------------------------------------------------
``GraphFeaturePreprocessor.transform()`` inserts its *entire* input edge list
into the in-memory graph and only then computes features "using the updated
graph" (snapml 1.17.2 docstring) -- so a single ``fit_transform(df)`` call over
a whole table lets every edge see every other edge in that same call,
including edges that happen later in time. There is no "compute without
inserting" method in the public API (``fit``, ``partial_fit``, ``transform``,
``fit_transform`` all insert).

The fix used here: batch edges into round windows via
``mritra.protocol.rounds.round_id_for_ts(ts, t0, round_window_sec)``
(PROTOCOL.md §10) and call ``transform()`` once per batch, in round order, on
one persistent ``GraphFeaturePreprocessor`` instance. Each call only ever has
batches ``<= b`` inserted into the graph, so a batch's features can never
depend on a *later* batch -- this is what the leakage test in
``tests/test_features.py`` checks, with real snapml. Edges within the *same*
batch (round) can still see each other (that is inherent to
``transform()``'s insert-then-compute behaviour and unavoidable without
calling it edge-by-edge, which is not practical at dataset scale); this
matches PREREGISTRATION §4's round-granularity leakage rule, not a stricter
same-batch exclusion. ``t0`` must be the same for every configuration
computing features in one experiment -- see ``compute_gfp_features``'s
docstring.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_gfp_config(path: Path | None = None) -> dict[str, Any]:
    """Load GFP settings from ``configs/gfp.yaml``."""
    if path is None:
        from mritra.config import CONFIG_DIR

        path = CONFIG_DIR / "gfp.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepare_edge_array(df: pd.DataFrame) -> np.ndarray:
    """Build the float64 edge array expected by GFP.

    Column order (per IBM examples):
        edge_id, src_id, dst_id, timestamp, amount [, extra …]

    ``src_id`` / ``dst_id`` are integer-encoded from (bank, acct) pairs so
    that identities are unique across the dataset.
    """
    # Create integer node IDs for (bank, acct) pairs
    all_nodes = pd.concat(
        [
            df[["from_bank", "from_acct"]].rename(
                columns={"from_bank": "bank", "from_acct": "acct"}
            ),
            df[["to_bank", "to_acct"]].rename(columns={"to_bank": "bank", "to_acct": "acct"}),
        ]
    ).drop_duplicates()
    all_nodes["node_id"] = np.arange(len(all_nodes), dtype=np.int64)
    node_map = dict(
        zip(
            zip(all_nodes["bank"], all_nodes["acct"], strict=True),
            all_nodes["node_id"],
            strict=True,
        )
    )

    src = np.array(
        [node_map[(b, a)] for b, a in zip(df["from_bank"], df["from_acct"], strict=True)],
        dtype=np.float64,
    )
    dst = np.array(
        [node_map[(b, a)] for b, a in zip(df["to_bank"], df["to_acct"], strict=True)],
        dtype=np.float64,
    )

    edge_id = df["row_id"].to_numpy(dtype=np.float64)
    ts = df["ts"].to_numpy(dtype=np.float64)
    amount = df["amt_paid"].to_numpy(dtype=np.float64)

    return np.column_stack([edge_id, src, dst, ts, amount])


# ---------------------------------------------------------------------------
# SnapML-based feature extraction
# ---------------------------------------------------------------------------


def compute_gfp_features(
    df: pd.DataFrame,
    t0: int,
    gfp_cfg: dict[str, Any] | None = None,
    round_window_sec: int | None = None,
) -> pd.DataFrame:
    """Run Graph Feature Preprocessor streaming in round-window batches.

    Parameters
    ----------
    df : DataFrame
        Transaction table (must have row_id, from_bank, from_acct, to_bank,
        to_acct, ts, amt_paid). Sorted by ``ts`` internally; need not be
        pre-sorted by the caller.
    t0 : int
        Round-zero anchor (PROTOCOL.md §10): the same value must be passed by
        every configuration (C1, C3, C4) computing features for one
        experiment, so round *N* means the identical wall-clock window
        everywhere, regardless of what slice of the timeline a particular
        call happens to see. No default -- see ``mritra.protocol.rounds``.
    gfp_cfg : dict, optional
        Overrides from ``configs/gfp.yaml``.
    round_window_sec : int, optional
        Batch width in seconds. Defaults to ``configs/experiment.yaml:
        protocol.round_window_sec`` (one simulated hour) via
        ``mritra.protocol.rounds.round_window_sec()``.

    Returns
    -------
    DataFrame with ``row_id`` as index and one column per GFP feature.
    """
    from mritra.protocol.rounds import round_id_for_ts
    from mritra.protocol.rounds import round_window_sec as _default_round_window_sec

    if gfp_cfg is None:
        gfp_cfg = load_gfp_config()
    if round_window_sec is None:
        round_window_sec = _default_round_window_sec()

    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    edge_arr = _prepare_edge_array(df)
    batch_id = round_id_for_ts(edge_arr[:, 3], t0, round_window_sec).astype(np.int64)

    try:
        from snapml import GraphFeaturePreprocessor  # type: ignore[import-untyped]

        gfp = GraphFeaturePreprocessor()
        for key, val in gfp_cfg.get("params", {}).items():
            setattr(gfp, key, val)

        outputs = []
        for b in np.unique(batch_id):  # ascending; edge_arr is ts-sorted so this is time order
            outputs.append(gfp.transform(edge_arr[batch_id == b]))
        result = np.concatenate(outputs, axis=0)
    except ImportError:
        logger.warning(
            "snapml not available — falling back to NetworkX stub features.  "
            "Install snapml on Linux for production graph features."
        )
        result = _networkx_stub_features(edge_arr, batch_id)

    # First 5 columns are the input (edge_id, src, dst, ts, amount); rest are features
    n_input_cols = 5
    n_feat = result.shape[1] - n_input_cols
    feat_names = [f"gfp_{i}" for i in range(n_feat)]
    row_ids = result[:, 0].astype(np.int64)
    features = result[:, n_input_cols:]

    feat_df = pd.DataFrame(features, columns=feat_names)
    feat_df.insert(0, "row_id", row_ids)
    return feat_df.set_index("row_id")


# ---------------------------------------------------------------------------
# NetworkX stub for environments without snapml
# ---------------------------------------------------------------------------


def _networkx_stub_features(edge_arr: np.ndarray, batch_id: np.ndarray) -> np.ndarray:
    """Compute basic graph stats via NetworkX as a stand-in for GFP.

    Builds the graph incrementally batch by batch (same round-window causality
    as the snapml path above): a batch's degree features reflect the graph
    after that batch is inserted, never a later one.

    Returns the original 5-column edge array with 6 appended stub features:
        src_out_degree, src_in_degree, dst_out_degree, dst_in_degree,
        src_total_degree, dst_total_degree
    """
    import networkx as nx

    G = nx.DiGraph()
    n = edge_arr.shape[0]
    feats = np.zeros((n, 6), dtype=np.float64)

    for b in np.unique(batch_id):
        idx = np.flatnonzero(batch_id == b)
        for i in idx:
            G.add_edge(int(edge_arr[i, 1]), int(edge_arr[i, 2]))

        out_deg = dict(G.out_degree())
        in_deg = dict(G.in_degree())
        for i in idx:
            s, d = int(edge_arr[i, 1]), int(edge_arr[i, 2])
            feats[i, 0] = out_deg.get(s, 0)
            feats[i, 1] = in_deg.get(s, 0)
            feats[i, 2] = out_deg.get(d, 0)
            feats[i, 3] = in_deg.get(d, 0)
            feats[i, 4] = feats[i, 0] + feats[i, 1]
            feats[i, 5] = feats[i, 2] + feats[i, 3]

    return np.hstack([edge_arr, feats])
