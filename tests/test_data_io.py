from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mritra.data.load import read_transactions
from mritra.data.patterns import (
    match_patterns_to_transactions,
    parse_patterns,
    pattern_cross_share,
)

FMT = "%Y/%m/%d %H:%M"
HEADER = (
    "Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,"
    "Amount Paid,Payment Currency,Payment Format,Is Laundering\n"
)
ROW_A = (
    "2022/09/01 00:20,10,8000EBD30,10,8000EBD30,3697.34,US Dollar,3697.34,US Dollar,"
    "Reinvestment,0\n"
)
ROW_B = "2022/09/01 00:06,021174,800737690,012,80011F990,2848.96,Euro,2848.96,Euro,ACH,1\n"


def test_read_transactions_renames_and_types_columns(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text(HEADER + ROW_A + ROW_B, encoding="utf-8")
    df, n_raw, _ = read_transactions(p, FMT, drop_exact_duplicates=False)
    assert n_raw == 2
    assert df["row_id"].tolist() == [0, 1]
    assert df.loc[1, "from_bank"] == 21174 and df.loc[1, "to_bank"] == 12
    assert df.loc[0, "ts"] == 1661991600  # 2022-09-01 00:20 UTC
    assert df.loc[1, "from_acct"] == "800737690"
    assert df["is_laund"].tolist() == [0, 1]


def test_duplicate_stats_always_computed_the_same_regardless_of_the_flag(
    tmp_path: Path,
) -> None:
    p = tmp_path / "t.csv"
    p.write_text(HEADER + ROW_A + ROW_B + ROW_A, encoding="utf-8")  # row 2 dups row 0
    _, n_raw_keep, dup_keep = read_transactions(p, FMT, drop_exact_duplicates=False)
    _, n_raw_drop, dup_drop = read_transactions(p, FMT, drop_exact_duplicates=True)
    assert n_raw_keep == n_raw_drop == 3
    assert dup_keep == dup_drop  # DuplicateStats computed before the flag is applied
    assert dup_keep.duplicate_rows == 1
    assert dup_keep.duplicate_rows_is_laund == 0  # the duplicated row (ROW_A) has is_laund=0


def test_drop_exact_duplicates_false_keeps_every_row(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text(HEADER + ROW_A + ROW_B + ROW_A, encoding="utf-8")
    df, _, _ = read_transactions(p, FMT, drop_exact_duplicates=False)
    assert len(df) == 3
    assert df["row_id"].tolist() == [0, 1, 2]


def test_drop_exact_duplicates_true_is_the_default_and_drops_later_occurrences(
    tmp_path: Path,
) -> None:
    p = tmp_path / "t.csv"
    p.write_text(HEADER + ROW_A + ROW_B + ROW_A, encoding="utf-8")
    df, _, _ = read_transactions(p, FMT)  # default: drop_exact_duplicates=True
    assert len(df) == 2
    assert df["row_id"].tolist() == [0, 1]  # row 2 (dup of row 0) dropped; row_id stable


def test_duplicate_stats_counts_is_laund_rows(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text(HEADER + ROW_B + ROW_B, encoding="utf-8")
    df, n_raw, dup_stats = read_transactions(p, FMT, drop_exact_duplicates=False)
    assert n_raw == 2
    assert len(df) == 2
    assert dup_stats.duplicate_rows == 1
    assert dup_stats.duplicate_rows_is_laund == 1  # ROW_B has is_laund=1


def test_read_transactions_rejects_unexpected_columns(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_transactions(p, FMT)


PATTERNS = """BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out
2022/09/01 00:06,021174,800737690,012,80011F990,2848.96,Euro,2848.96,Euro,ACH,1
2022/09/01 04:32,021174,800737690,020,80020C5B0,8630.40,Euro,8630.40,Euro,ACH,1
END LAUNDERING ATTEMPT - FAN-OUT

BEGIN LAUNDERING ATTEMPT - STACK
2022/09/02 10:00,012,80011F990,012,8001AAAA0,100.00,Euro,100.00,Euro,Cash,1
END LAUNDERING ATTEMPT - STACK
"""


def test_parse_patterns(tmp_path: Path) -> None:
    p = tmp_path / "p.txt"
    p.write_text(PATTERNS, encoding="utf-8")
    df = parse_patterns(p, FMT)
    assert df["pattern_id"].tolist() == [0, 0, 1]
    assert df["pattern_type"].tolist() == ["FAN-OUT", "FAN-OUT", "STACK"]
    assert df.loc[0, "pattern_detail"] == "Max 16-degree Fan-Out"
    assert df.loc[0, "from_bank"] == 21174

    per = pattern_cross_share(df, {21174: 0, 12: 1, 20: 1})
    assert per["cross"].tolist() == [True, False]
    assert per["n_inst"].tolist() == [2, 1]
    # pattern 0 (FAN-OUT): both its edges cross (21174@0 -> 12@1, 21174@0 -> 20@1)
    # pattern 1 (STACK): single edge is within institution 1 (12 -> 12)
    assert per["cross_any_edge"].tolist() == [True, False]


def test_pattern_cross_share_distinguishes_touch_from_any_edge() -> None:
    # A pattern that touches 2 institutions (0 and 1) but whose two transactions are
    # each entirely within one institution — "cross" (primary) is True, but no single
    # edge crosses, so "cross_any_edge" is False.
    df = pd.DataFrame(
        {
            "pattern_id": [0, 0],
            "pattern_type": pd.Categorical(["FAN-OUT", "FAN-OUT"]),
            "from_bank": [1, 2],
            "to_bank": [1, 2],
        }
    )
    per = pattern_cross_share(df, {1: 0, 2: 1})
    assert per["n_inst"].tolist() == [2]
    assert per["cross"].tolist() == [True]
    assert per["cross_any_edge"].tolist() == [False]


def test_parse_patterns_rejects_unclosed(tmp_path: Path) -> None:
    p = tmp_path / "p.txt"
    p.write_text(PATTERNS.split("END")[0], encoding="utf-8")
    with pytest.raises(ValueError):
        parse_patterns(p, FMT)


def test_match_patterns_to_transactions(tmp_path: Path) -> None:
    trans_p = tmp_path / "t.csv"
    # ROW_B appears in trans; ROW_A (not laundering) does not — simulates a pattern row
    # with no counterpart in the transaction table.
    trans_p.write_text(HEADER + ROW_B, encoding="utf-8")
    trans, _, _ = read_transactions(trans_p, FMT)

    patterns_p = tmp_path / "p.txt"
    patterns_p.write_text(PATTERNS, encoding="utf-8")
    patterns = parse_patterns(patterns_p, FMT)

    result = match_patterns_to_transactions(trans, patterns)
    assert result["pattern_rows"] == 3
    assert result["matched_pattern_rows"] == 1  # only the row equal to ROW_B matches
    assert result["pattern_to_transaction_match_rate"] == pytest.approx(1 / 3)
    assert result["laundering_txns_total"] == 1  # ROW_B
    assert result["laundering_txns_not_in_any_pattern"] == 0  # ROW_B is in the patterns file


STACK_ROW = "2022/09/02 10:00,012,80011F990,012,8001AAAA0,100.00,Euro,100.00,Euro,Cash,1\n"


def test_match_patterns_to_transactions_reports_match_multiplicity(tmp_path: Path) -> None:
    # 3 pattern rows total: the FAN-OUT row equal to ROW_B, a second unique FAN-OUT row,
    # and the STACK row.
    # trans has: ROW_B duplicated twice (-> that pattern row matches 2 txns, "gt1"),
    # the STACK row once (-> matches exactly 1), and nothing matching the second
    # FAN-OUT row (-> matches 0).
    trans_p = tmp_path / "t.csv"
    trans_p.write_text(HEADER + ROW_B + ROW_B + STACK_ROW, encoding="utf-8")
    trans, _, _ = read_transactions(trans_p, FMT, drop_exact_duplicates=False)

    patterns_p = tmp_path / "p.txt"
    patterns_p.write_text(PATTERNS, encoding="utf-8")
    patterns = parse_patterns(patterns_p, FMT)

    result = match_patterns_to_transactions(trans, patterns)
    assert result["pattern_rows"] == 3
    assert result["pattern_rows_matching_0"] == 1  # the unique second FAN-OUT row
    assert result["pattern_rows_matching_1"] == 1  # STACK
    assert result["pattern_rows_matching_gt1"] == 1  # ROW_B's pattern row, 2 txn matches
    assert result["matched_pattern_rows"] == 2  # matching_1 + matching_gt1, NOT a joined-row count
    assert result["pattern_to_transaction_match_rate"] == pytest.approx(2 / 3)
    assert result["laundering_txns_total"] == 3  # ROW_B x2 + STACK_ROW, all is_laund=1
    assert result["laundering_txns_not_in_any_pattern"] == 0
