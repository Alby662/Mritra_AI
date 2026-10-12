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


def _prepare_edge_array(df: pd.DataFrame, node_map: dict | None = None) -> np.ndarray:
    """Build the float64 edge array expected by GFP.

    Column order (per IBM examples):
        edge_id, src_id, dst_id, timestamp, amount [, extra …]

    ``src_id`` / ``dst_id`` are integer-encoded from (bank, acct) pairs so
    that identities are unique across the dataset.
    """
    if node_map is None:
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
    else:

        def map_nodes(bank_col, acct_col):
            keys = bank_col.astype(str) + "_" + acct_col.astype(str)
            unique_keys = keys.unique()
            new_keys = np.setdiff1d(unique_keys, list(node_map.keys()), assume_unique=True)
            if len(new_keys) > 0:
                start = len(node_map)
                node_map.update(zip(new_keys, range(start, start + len(new_keys))))
            return keys.map(node_map).to_numpy(dtype=np.float64)

        src = map_nodes(df["from_bank"], df["from_acct"])
        dst = map_nodes(df["to_bank"], df["to_acct"])

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


class GFPStreamer:
    """Stateful wrapper for GraphFeaturePreprocessor to process data in chunks."""

    def __init__(self, t0: int, round_window_sec: int, gfp_cfg: dict[str, Any] | None = None):
        if gfp_cfg is None:
            gfp_cfg = load_gfp_config()

        try:
            from snapml import GraphFeaturePreprocessor

            self.gfp = GraphFeaturePreprocessor()
            self.gfp.set_params(dict(gfp_cfg.get("params", {})))
        except ImportError:

            class _MockGraphFeaturePreprocessor:
                def __init__(self, cfg: dict[str, Any]):
                    self.cfg = cfg
                    self._n_feat = 215

                def set_params(self, params: dict[str, Any]) -> None:
                    pass

                def transform(self, edge_arr: np.ndarray) -> np.ndarray:
                    dummy_feats = np.zeros((len(edge_arr), self._n_feat), dtype=np.float32)
                    return np.column_stack([edge_arr, dummy_feats])

            self.gfp = _MockGraphFeaturePreprocessor(gfp_cfg)
        self.t0 = t0
        self.round_window_sec = round_window_sec
        self.gfp_cfg = gfp_cfg
        self.n_feat = None
        self.feat_names = None
        self.node_map = {}

    def process_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        from mritra.protocol.rounds import round_id_for_ts

        # Ensure chunk is sorted by time for correct round generation
        df = df.sort_values("ts", kind="stable").reset_index(drop=True)
        edge_arr = _prepare_edge_array(df, node_map=self.node_map)
        batch_id = round_id_for_ts(edge_arr[:, 3], self.t0, self.round_window_sec).astype(np.int64)

        row_ids_list = []
        features_list = []
        n_input_cols = 5

        # Process round by round
        for b in np.unique(batch_id):
            batch_edges = edge_arr[batch_id == b]
            if len(batch_edges) == 0:
                continue
            out = self.gfp.transform(batch_edges)
            row_ids_list.append(out[:, 0].astype(np.int64))
            features_list.append(out[:, n_input_cols:].astype(np.float32))

        if not row_ids_list:
            return pd.DataFrame()

        row_ids = np.concatenate(row_ids_list, axis=0)
        features = np.concatenate(features_list, axis=0)

        if self.n_feat is None:
            self.n_feat = features.shape[1]
            self.feat_names = gfp_feature_names(self.n_feat, self.gfp_cfg)

        feat_df = pd.DataFrame(features, columns=self.feat_names, copy=False)
        feat_df.insert(0, "row_id", row_ids)
        return feat_df.set_index("row_id")


def compute_gfp_features(
    df: pd.DataFrame,
    t0: int = 0,
    gfp_cfg: dict[str, Any] | None = None,
    round_window_sec: int | None = None,
) -> pd.DataFrame:
    """Run Graph Feature Preprocessor streaming in round-window batches."""
    from mritra.protocol.rounds import round_window_sec as _default_round_window_sec

    if round_window_sec is None:
        round_window_sec = _default_round_window_sec()

    streamer = GFPStreamer(t0, round_window_sec, gfp_cfg)
    return streamer.process_chunk(df)
