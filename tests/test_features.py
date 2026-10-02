"""No-future-leakage tests for feature code (CLAUDE.md §6: "feature at t unchanged when
later rows are appended").

Covers behaviour.py and graph_gfp.py (round-windowed streaming, see its module docstring
for why and how). network.py is tested separately once it has an ``as_of`` cutoff.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mritra.features.behaviour import compute_behavioural_features
from mritra.features.graph_gfp import compute_gfp_features, load_gfp_config


def _toy_transactions(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    insts = [0, 1]
    accts = ["A", "B", "C"]
    rows = []
    for i in range(n):
        fi, ti = rng.choice(insts, size=2, replace=False)
        fa, ta = rng.choice(accts, size=2, replace=False)
        rows.append(
            {
                "row_id": i,
                "ts": 1_000 + i * 100,
                "from_inst": fi,
                "from_acct": fa,
                "to_inst": ti,
                "to_acct": ta,
                "amt_paid": 100.0 + i,
                "amt_recv": 95.0 + i,
                "fmt": rng.choice(["ACH", "Wire"]),
                "cur_paid": "USD",
            }
        )
    return pd.DataFrame(rows)


def test_behavioural_features_unchanged_when_future_rows_appended() -> None:
    df = _toy_transactions(n=25, seed=1)
    cutoff = 15

    before = compute_behavioural_features(df.iloc[:cutoff].copy())
    after = compute_behavioural_features(df.copy())  # 10 more rows, all ts > cutoff's rows

    shared_ids = before.index
    pd.testing.assert_frame_equal(
        before.loc[shared_ids].sort_index(),
        after.loc[shared_ids].sort_index(),
        check_like=False,
    )


def _toy_graph_edges(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    accounts = ["A", "B", "C", "D", "E"]
    rows = []
    for i in range(n):
        f, t = rng.choice(accounts, size=2, replace=False)
        rows.append(
            {
                "row_id": i,
                "from_bank": 0,
                "from_acct": f,
                "to_bank": 1,
                "to_acct": t,
                "ts": 1_000 + i * 300,  # 5 min apart -> several round-window batches
                "amt_paid": 100.0 + i,
            }
        )
    return pd.DataFrame(rows)


def test_graph_gfp_features_unchanged_for_earlier_batches_real_snapml() -> None:
    pytest.importorskip("snapml")
    df = _toy_graph_edges(n=60, seed=0)
    round_window_sec = 3600

    # Cut at a round-window BOUNDARY, not an arbitrary row count: transform() computes a
    # batch's features from the graph *after* that whole batch is inserted (snapml
    # docstring), so edges within the same batch legitimately see each other. Truncating
    # mid-batch would make the last partial batch differ for a reason that has nothing to
    # do with future leakage -- see the session report for the exploratory version of this
    # test that did that and was misleading.
    batch_id = df["ts"] // round_window_sec
    b_cut = batch_id.iloc[40]
    earlier_batches = df[batch_id <= b_cut].copy()

    cfg = load_gfp_config()
    before = compute_gfp_features(earlier_batches, cfg, round_window_sec=round_window_sec)
    after = compute_gfp_features(df.copy(), cfg, round_window_sec=round_window_sec)

    shared_ids = before.index
    pd.testing.assert_frame_equal(
        before.loc[shared_ids].sort_index(),
        after.loc[shared_ids].sort_index(),
        check_like=False,
    )
