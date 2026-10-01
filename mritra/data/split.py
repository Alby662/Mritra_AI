"""Temporal train/validation/test split (PREREGISTRATION §4)."""

from __future__ import annotations

import numpy as np
import pandas as pd

SPLITS = ("train", "val", "test")


def temporal_split(ts: pd.Series, train: float, val: float) -> pd.Series:
    """Label each row train/val/test by timestamp order and row-count fractions.

    Rows are ordered by a stable sort on `ts`. Cut points are at floor(n*train) and
    floor(n*(train+val)); every row sharing the timestamp of the last row before a cut
    goes to the earlier split, so no timestamp straddles two splits.
    """
    n = len(ts)
    values = ts.to_numpy()
    order = np.argsort(values, kind="stable")
    sorted_ts = values[order]

    labels = np.empty(n, dtype=object)
    start = 0
    for name, frac_end in (("train", train), ("val", train + val)):
        cut = int(np.floor(n * frac_end))
        if cut > start:
            # extend the cut past all rows sharing the boundary timestamp
            cut = int(np.searchsorted(sorted_ts, sorted_ts[cut - 1], side="right"))
        cut = max(cut, start)
        labels[order[start:cut]] = name
        start = cut
    labels[order[start:]] = "test"
    return pd.Series(pd.Categorical(labels, categories=SPLITS), index=ts.index, name="split")
