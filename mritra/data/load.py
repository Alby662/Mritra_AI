"""Load the AMLworld transaction CSV into a typed DataFrame.

Does NOT drop duplicate rows. PREREGISTRATION.md §3 currently says to drop exact
duplicates, but nothing is dropped here until that is confirmed against the real data —
see DuplicateStats and DECISIONS.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_COLUMNS = [
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account.1",  # pandas' name for the second "Account" column
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
]
COLUMNS = [
    "ts",
    "from_bank",
    "from_acct",
    "to_bank",
    "to_acct",
    "amt_recv",
    "cur_recv",
    "amt_paid",
    "cur_paid",
    "fmt",
    "is_laund",
]
CATEGORY_COLUMNS = ["from_acct", "to_acct", "cur_recv", "cur_paid", "fmt"]


@dataclass(frozen=True)
class DuplicateStats:
    """Exact-duplicate rows found (not removed). All COLUMNS match, including is_laund."""

    duplicate_rows: int  # rows beyond the first occurrence of each exact duplicate group
    duplicate_rows_is_laund: int  # of those, how many have is_laund == 1


def read_transactions(
    path: Path, timestamp_format: str
) -> tuple[pd.DataFrame, int, DuplicateStats]:
    """Read the raw CSV and rename/type columns. Does not drop anything.

    Returns the frame, the raw row count, and exact-duplicate-row stats computed but not
    acted on (see module docstring). `row_id` is the 0-based row position in the raw CSV;
    it is the transaction's stable identity (and the protocol's `edge_ref`).
    """
    df = pd.read_csv(
        path,
        dtype={
            "From Bank": "int64",
            "To Bank": "int64",
            "Account": "string",
            "Account.1": "string",
            "Amount Received": "float64",
            "Amount Paid": "float64",
            "Is Laundering": "int8",
        },
    )
    if list(df.columns) != RAW_COLUMNS:
        raise ValueError(f"Unexpected columns in {path}: {list(df.columns)}")
    n_raw = len(df)
    df.columns = COLUMNS
    df.insert(0, "row_id", pd.RangeIndex(n_raw, dtype="int64"))

    dup_mask = df.duplicated(subset=COLUMNS, keep="first")
    dup_stats = DuplicateStats(
        duplicate_rows=int(dup_mask.sum()),
        duplicate_rows_is_laund=int(df.loc[dup_mask, "is_laund"].eq(1).sum()),
    )
    logger.info(
        "rows raw=%d exact_duplicates=%d (is_laund=1: %d) — NOT dropped",
        n_raw,
        dup_stats.duplicate_rows,
        dup_stats.duplicate_rows_is_laund,
    )

    df["ts"] = pd.to_datetime(df["ts"], format=timestamp_format, utc=True).astype("int64") // 10**9
    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")
    # Amounts kept as float64: float32 loses cents above ~$170k, which would break
    # double-entry reconciliation on exact amounts.
    return df.reset_index(drop=True), n_raw, dup_stats
