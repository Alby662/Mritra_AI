"""No-future-leakage tests for feature code (CLAUDE.md §6: "feature at t unchanged when
later rows are appended").

Only behaviour.py is covered here. graph_gfp.py and network.py were tested with the same
method and both FAILED (reproducible, documented separately) — see DECISIONS.md / the
session report. Per instruction, those failures are reported, not silently fixed or
marked around, so they are deliberately not included as tests in this file yet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mritra.features.behaviour import compute_behavioural_features


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
