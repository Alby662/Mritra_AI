"""IBM Graph Feature Preprocessor (GFP) wrapper (plan §7.1).

Wraps ``snapml.GraphFeaturePreprocessor`` to produce edge-level graph features
(fan-in/out, degree, scatter-gather, temporal-cycle, etc.) from the AMLworld
transaction table.  Falls back to a minimal NetworkX stub when snapml is not
installed (e.g. on macOS or Windows) so the rest of the pipeline can still run.
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
            df[["to_bank", "to_acct"]].rename(
                columns={"to_bank": "bank", "to_acct": "acct"}
            ),
        ]
    ).drop_duplicates()
    all_nodes["node_id"] = np.arange(len(all_nodes), dtype=np.int64)
    node_map = dict(zip(zip(all_nodes["bank"], all_nodes["acct"], strict=True), all_nodes["node_id"]))

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
    gfp_cfg: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Run Graph Feature Preprocessor and return edge-level features.

    Parameters
    ----------
    df : DataFrame
        Transaction table (must have row_id, from_bank, from_acct, to_bank,
        to_acct, ts, amt_paid).  Must be sorted by ``ts``.
    gfp_cfg : dict, optional
        Overrides from ``configs/gfp.yaml``.

    Returns
    -------
    DataFrame with ``row_id`` as index and one column per GFP feature.
    """
    if gfp_cfg is None:
        gfp_cfg = load_gfp_config()

    edge_arr = _prepare_edge_array(df)

    try:
        from snapml import GraphFeaturePreprocessor  # type: ignore[import-untyped]

        gfp = GraphFeaturePreprocessor()
        for key, val in gfp_cfg.get("params", {}).items():
            setattr(gfp, key, val)
        result = gfp.fit_transform(edge_arr)
    except ImportError:
        logger.warning(
            "snapml not available — falling back to NetworkX stub features.  "
            "Install snapml on Linux for production graph features."
        )
        result = _networkx_stub_features(edge_arr)

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


def _networkx_stub_features(edge_arr: np.ndarray) -> np.ndarray:
    """Compute basic graph stats via NetworkX as a stand-in for GFP.

    Returns the original 5-column edge array with 6 appended stub features:
        src_out_degree, src_in_degree, dst_out_degree, dst_in_degree,
        src_total_degree, dst_total_degree
    """
    import networkx as nx

    G = nx.DiGraph()
    for row in edge_arr:
        src, dst = int(row[1]), int(row[2])
        G.add_edge(src, dst)

    out_deg = dict(G.out_degree())
    in_deg = dict(G.in_degree())

    n = edge_arr.shape[0]
    feats = np.zeros((n, 6), dtype=np.float64)
    for i, row in enumerate(edge_arr):
        s, d = int(row[1]), int(row[2])
        feats[i, 0] = out_deg.get(s, 0)
        feats[i, 1] = in_deg.get(s, 0)
        feats[i, 2] = out_deg.get(d, 0)
        feats[i, 3] = in_deg.get(d, 0)
        feats[i, 4] = feats[i, 0] + feats[i, 1]
        feats[i, 5] = feats[i, 2] + feats[i, 3]

    return np.hstack([edge_arr, feats])
