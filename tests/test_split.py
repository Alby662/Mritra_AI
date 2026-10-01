from __future__ import annotations

import pandas as pd

from mritra.data.split import temporal_split


def test_exact_fractions_without_ties() -> None:
    ts = pd.Series(range(10))
    split = temporal_split(ts, 0.6, 0.2)
    assert split.value_counts().to_dict() == {"train": 6, "val": 2, "test": 2}
    assert split.tolist() == ["train"] * 6 + ["val"] * 2 + ["test"] * 2


def test_boundary_timestamp_ties_go_to_earlier_split() -> None:
    # train cut after row 6 lands inside the run of ts=5 -> both ts=5 rows are train (7);
    # val cut after row 8 lands on ts=6 -> val is just that row
    ts = pd.Series([0, 1, 2, 3, 4, 5, 5, 6, 8, 9])
    split = temporal_split(ts, 0.6, 0.2)
    assert split.tolist() == ["train"] * 7 + ["val"] + ["test"] * 2


def test_unsorted_input_keeps_index_and_no_timestamp_straddles() -> None:
    ts = pd.Series([9, 0, 5, 3, 5, 1, 6, 2, 4, 8], index=list("abcdefghij"))
    split = temporal_split(ts, 0.6, 0.2)
    assert list(split.index) == list("abcdefghij")
    per_ts = pd.DataFrame({"ts": ts, "s": split}).groupby("ts")["s"].nunique()
    assert (per_ts == 1).all()
    order = {"train": 0, "val": 1, "test": 2}
    ranks = split.map(order).astype(int)
    # splits are monotone in time
    assert (
        ts[ranks == 0].max() < ts[ranks == 1].min() <= ts[ranks == 1].max() < ts[ranks == 2].min()
    )


def test_splits_can_be_empty_when_ties_swallow_them() -> None:
    ts = pd.Series([1] * 5)
    assert temporal_split(ts, 0.6, 0.2).tolist() == ["train"] * 5
