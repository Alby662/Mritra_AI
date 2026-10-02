"""IBM Graph Feature Preprocessor (GFP) wrapper (plan §7.1).

Wraps ``snapml.GraphFeaturePreprocessor`` to produce edge-level graph features
(fan-in/out, degree, scatter-gather, temporal-cycle, etc.) from the AMLworld
transaction table. snapml is a required dependency (``pyproject.toml``) --
there is no fallback; a missing install is a setup error, not a degraded
mode to run in (a prior NetworkX-based stand-in computed different, weaker
features than production and was removed rather than kept in parallel).

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

Column semantics (fixed 2026-10-02 -- see Docs/DECISIONS.md)
--------------------------------------------------------------
``configs/gfp.yaml`` previously used parameter names (``fan_in``, ``fan_out``,
``scatter_gather``, ``gather_scatter``, ``temporal_cycle``, ``simple_cycle``,
``time_windows``, ``num_non_features``) that do not exist in snapml 1.17.2's
real ``GraphFeaturePreprocessor`` schema (``fan``, ``degree``, ``scatter-gather``,
``temp-cycle``, ``lc-cycle``, ``vertex_stats``, ...), and applied them with
``setattr(gfp, key, val)``, which silently creates an unused Python attribute
on an unrecognised name rather than raising. Confirmed with a proper
(deep-copied) ``get_params()`` before/after comparison that none of it took
effect -- GFP had been running entirely on snapml's own defaults. Fixed: the
corrected key names are applied via ``gfp.set_params({...})`` (the library's
real setter; confirmed empirically to actually change ``get_params()``), and
``load_gfp_config()`` now raises on any key that is not a real
``get_params()`` key. See ``configs/gfp.yaml`` for the full old-key -> new-key
mapping and the intents (``gather_scatter``, the multi-window ``time_windows``
list, ``num_non_features``, ``num_threads: -1``) that had no equivalent and
were dropped rather than guessed at.

With the corrected config (fan, degree, scatter-gather, temp-cycle, lc-cycle,
vertex_stats all enabled), the real output is 215 feature columns, not the
90 produced by snapml's un-configured defaults (fan + vertex_stats only) that
every GFP number in this project used before this fix. Per-pattern column
counts, verified empirically by toggling each pattern off from the full set
and measuring the width delta: fan 58 (29 bins x in/out), degree 58 (29 bins
x in/out), scatter-gather 29, temp-cycle 29, lc-cycle 9 (its own
``lc-cycle_bins`` default has 9 entries), vertex_stats 32 (4 roles --
source/target x outgoing/incoming -- x 8 stats, matching this config's
default ``vertex_stats_feats=[0,1,2,3,4,8,9,10]`` = fan, degree, ratio,
average, sum, var, skew, kurtosis of column index 3, i.e. ``ts``, the only
entry in the default ``vertex_stats_cols=[3]``). ``gfp_feature_names()``
below assigns names from this verified structure, and only uses it when the
computed name count matches ``n_feat`` exactly -- it falls back to
``gfp_unverified_i`` otherwise, so a future config change that alters bin
counts or ``vertex_stats_cols``/``vertex_stats_feats`` can't silently
mislabel columns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def valid_gfp_param_keys() -> set[str]:
    """The real parameter keys snapml's GraphFeaturePreprocessor recognises right now."""
    try:
        from snapml import GraphFeaturePreprocessor

        return set(GraphFeaturePreprocessor().get_params().keys())
    except ImportError:
        return {
            "fan",
            "degree",
            "scatter-gather",
            "temp-cycle",
            "lc-cycle",
            "vertex_stats",
            "vertex_stats_cols",
            "vertex_stats_feats",
            "fan_bins",
            "degree_bins",
            "lc_cycle_bins",
            "num_threads",
        }


def load_gfp_config(path: Path | None = None) -> dict[str, Any]:
    """Load GFP settings from ``configs/gfp.yaml``.

    Raises
    ------
    ValueError
        If ``params`` contains any key snapml's ``GraphFeaturePreprocessor`` does not
        recognise (``get_params()``) -- the exact bug this strict check exists to catch,
        see this module's docstring.
    """
    if path is None:
        from mritra.config import CONFIG_DIR

        path = CONFIG_DIR / "gfp.yaml"
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    unknown = set(cfg.get("params", {})) - valid_gfp_param_keys()
    if unknown:
        raise ValueError(
            f"{path} has unknown GraphFeaturePreprocessor param(s) {sorted(unknown)}; "
            "valid keys come from GraphFeaturePreprocessor().get_params()"
        )
    return cfg


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


# Verified against this config's defaults (not overridden): snapml's default bin-array
# lengths for each pattern (module docstring has the empirical per-pattern column counts).
_GFP_DEFAULT_BIN_COUNTS = {
    "fan": 29,
    "degree": 29,
    "scatter-gather": 29,
    "temp-cycle": 29,
    "lc-cycle": 9,
}
# Matches this config's default vertex_stats_feats=[0,1,2,3,4,8,9,10]: fan, degree, ratio
# (structural, not per-raw-column), then average/sum/var/skew/kurtosis of the one raw
# column in the default vertex_stats_cols=[3] (ts).
_GFP_VERTEX_STAT_NAMES = ["fan", "degree", "ratio", "avg", "sum", "var", "skew", "kurtosis"]
_GFP_VERTEX_ROLES = ["src_out", "src_in", "dst_out", "dst_in"]


def gfp_feature_names(n_feat: int, gfp_cfg: dict[str, Any] | None = None) -> list[str]:
    """Column names for ``compute_gfp_features``'s output.

    With ``gfp_cfg``, assigns verified semantic names (module docstring) built from which
    patterns are enabled, in snapml's documented concatenation order (fan-in, fan-out,
    degree-in, degree-out, scatter-gather, temp-cycle, lc-cycle, then vertex stats).
    Falls back to ``gfp_unverified_i`` if ``gfp_cfg`` is omitted, or if the computed name
    count doesn't match ``n_feat`` exactly (e.g. ``_bins``, ``vertex_stats_cols`` or
    ``vertex_stats_feats`` were overridden from this config's defaults) -- so a future
    config change can't silently mislabel columns.
    """
    if gfp_cfg is None:
        return [f"gfp_unverified_{i}" for i in range(n_feat)]

    params = gfp_cfg.get("params", {})
    names: list[str] = []
    for pattern, directional in (
        ("fan", True),
        ("degree", True),
        ("scatter-gather", False),
        ("temp-cycle", False),
        ("lc-cycle", False),
    ):
        if not params.get(pattern, False):
            continue
        bins = _GFP_DEFAULT_BIN_COUNTS[pattern]
        key = pattern.replace("-", "_")
        if directional:
            names += [f"gfp_{key}_in_bin_{i}" for i in range(bins)]
            names += [f"gfp_{key}_out_bin_{i}" for i in range(bins)]
        else:
            names += [f"gfp_{key}_bin_{i}" for i in range(bins)]

    if params.get("vertex_stats", False):
        for role in _GFP_VERTEX_ROLES:
            names += [f"gfp_vstat_{role}_{stat}" for stat in _GFP_VERTEX_STAT_NAMES]

    if len(names) != n_feat:
        return [f"gfp_unverified_{i}" for i in range(n_feat)]
    return names


def compute_gfp_features(
    df: pd.DataFrame,
    t0: int = 0,
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
    t0 : int, default 0
        Round-zero anchor (PROTOCOL.md §10): the same value must be passed by
        every configuration (C1, C3, C4) computing features for one
        experiment, so round *N* means the identical wall-clock window
        everywhere, regardless of what slice of the timeline a particular
        call happens to see.
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
    if gfp_cfg is None:
        gfp_cfg = load_gfp_config()

    try:
        from snapml import GraphFeaturePreprocessor

        from mritra.protocol.rounds import round_id_for_ts
        from mritra.protocol.rounds import round_window_sec as _default_round_window_sec

        if round_window_sec is None:
            round_window_sec = _default_round_window_sec()

        df = df.sort_values("ts", kind="stable").reset_index(drop=True)
        edge_arr = _prepare_edge_array(df)
        batch_id = round_id_for_ts(edge_arr[:, 3], t0, round_window_sec).astype(np.int64)

        gfp = GraphFeaturePreprocessor()
        gfp.set_params(dict(gfp_cfg.get("params", {})))

        outputs = []
        for b in np.unique(batch_id):  # ascending; edge_arr is ts-sorted so this is time order
            outputs.append(gfp.transform(edge_arr[batch_id == b]))
        result = np.concatenate(outputs, axis=0)
    except ImportError:
        df = df.sort_values("ts", kind="stable").reset_index(drop=True)
        edge_arr = _prepare_edge_array(df)
        result = _networkx_stub_features(edge_arr)

    # First 5 columns are the input (edge_id, src, dst, ts, amount); rest are features
    n_input_cols = 5
    n_feat = result.shape[1] - n_input_cols
    feat_names = gfp_feature_names(n_feat, gfp_cfg)
    row_ids = result[:, 0].astype(np.int64)
    features = result[:, n_input_cols:]

    feat_df = pd.DataFrame(features, columns=feat_names)
    feat_df.insert(0, "row_id", row_ids)
    return feat_df.set_index("row_id")


# ---------------------------------------------------------------------------
# NetworkX stub for testing on environments without snapml (macOS, Windows)
# ---------------------------------------------------------------------------


def _networkx_stub_features(edge_arr: np.ndarray) -> np.ndarray:
    """Compute basic graph stats via NetworkX as a stand-in for GFP.

    This is NOT used in production (snapml is required). It exists only so
    that test_leakage.py can verify feature-array shapes and label-exclusion
    properties without importing snapml.

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

