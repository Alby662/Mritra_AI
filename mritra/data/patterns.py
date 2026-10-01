"""Parse the AMLworld Patterns file into one row per (pattern, transaction)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from mritra.data.load import COLUMNS

_BEGIN = re.compile(r"^BEGIN LAUNDERING ATTEMPT\s*-\s*(?P<type>[^:]+?)\s*(?::\s*(?P<detail>.*))?$")
_END = "END LAUNDERING ATTEMPT"


def parse_patterns(path: Path, timestamp_format: str) -> pd.DataFrame:
    """Return columns pattern_id, pattern_type, pattern_detail + the transaction COLUMNS.

    Header lines look like `BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out`;
    each following line is one transaction in Trans-file column order. Bank IDs are parsed
    as integers so zero-padded IDs match the Trans file.
    """
    rows: list[list[object]] = []
    pattern_id = -1
    ptype: str | None = None
    detail = ""
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            m = _BEGIN.match(line)
            if m:
                if ptype is not None:
                    raise ValueError(f"{path}:{lineno}: BEGIN inside an open pattern")
                pattern_id += 1
                ptype = m.group("type").strip().upper()
                detail = (m.group("detail") or "").strip()
            elif line.startswith(_END):
                if ptype is None:
                    raise ValueError(f"{path}:{lineno}: END without BEGIN")
                ptype = None
            elif ptype is not None:
                fields = line.split(",")
                if len(fields) != len(COLUMNS):
                    raise ValueError(f"{path}:{lineno}: expected {len(COLUMNS)} fields")
                rows.append([pattern_id, ptype, detail, *fields])
    if ptype is not None:
        raise ValueError(f"{path}: file ends inside a pattern")

    df = pd.DataFrame(rows, columns=["pattern_id", "pattern_type", "pattern_detail", *COLUMNS])
    df["pattern_id"] = df["pattern_id"].astype("int32")
    df["pattern_type"] = df["pattern_type"].astype("category")
    df["ts"] = pd.to_datetime(df["ts"], format=timestamp_format, utc=True).astype("int64") // 10**9
    for col in ("from_bank", "to_bank"):
        df[col] = df[col].astype("int64")
    for col in ("amt_recv", "amt_paid"):
        df[col] = df[col].astype("float64")
    df["is_laund"] = df["is_laund"].astype("int8")
    return df


def pattern_cross_share(patterns: pd.DataFrame, inst_of: dict[int, int]) -> pd.DataFrame:
    """Per pattern: its type and two cross-institution variants.

    `cross` (PRIMARY, quoting PREREGISTRATION.md §4): "A laundering attempt in the
    Patterns file whose transactions touch > 1 institution" — i.e. the set of
    institutions touched by any of the pattern's transactions (sender or receiver) has
    size > 1. This is what the H1 gate is evaluated against.

    `cross_any_edge` (SECONDARY, not in PREREGISTRATION.md, reported for comparison): at
    least one single transaction in the pattern has sender institution != receiver
    institution. A pattern can touch > 1 institution with every individual transaction
    staying within one institution (e.g. two different within-institution legs at two
    different institutions), so this is not the same number as `cross`.
    """
    keys = patterns[["pattern_id", "pattern_type"]]
    from_inst = patterns["from_bank"].map(inst_of)
    to_inst = patterns["to_bank"].map(inst_of)
    if from_inst.isna().any() or to_inst.isna().any():
        raise ValueError("Patterns file references banks missing from the partition")

    insts = pd.concat([keys.assign(inst=from_inst), keys.assign(inst=to_inst)])
    per = insts.groupby("pattern_id", observed=True).agg(
        pattern_type=("pattern_type", "first"), n_inst=("inst", "nunique")
    )
    per["cross"] = per["n_inst"] > 1

    edge_cross = (from_inst != to_inst).groupby(patterns["pattern_id"], observed=True).any()
    per["cross_any_edge"] = edge_cross
    return per


# ts, from_bank, from_acct, to_bank, to_acct, amounts, currencies, fmt, is_laund
MATCH_KEY_COLUMNS = COLUMNS


def match_patterns_to_transactions(trans: pd.DataFrame, patterns: pd.DataFrame) -> dict:
    """Exact-field match rate between Patterns-file rows and the main transaction table.

    Matches on every COLUMNS field (full row content, not row_id — the Patterns file
    carries no row_id). For each pattern row we count how many transaction rows share its
    key (0, 1, or >1 — the trans table can itself hold exact duplicates), via a
    groupby-count join: the right side of the merge has exactly one row per distinct key,
    so every pattern row contributes exactly one row to the result regardless of how many
    transactions share its key. That keeps the match rate computed over unique pattern
    rows, not over a join that could silently multiply rows.

    Also reports how many laundering transactions in `trans` match no pattern row
    (DATA.md §9: "not every laundering transaction belongs to a Patterns-file attempt").
    """
    key = MATCH_KEY_COLUMNS
    trans_match_counts = trans.groupby(key, observed=True).size().reset_index(name="n_matches")
    n_matches = (
        patterns[key]
        .merge(trans_match_counts, on=key, how="left")["n_matches"]
        .fillna(0)
        .astype("int64")
    )

    pattern_keys = patterns[key].drop_duplicates()
    pattern_keys["_in_pattern"] = True
    laund = trans.loc[trans["is_laund"] == 1, key]
    laund_matched = laund.merge(pattern_keys, on=key, how="left")["_in_pattern"].notna()

    n_patterns = len(patterns)
    matched = n_matches >= 1
    return {
        "pattern_rows": n_patterns,
        "pattern_rows_matching_0": int((n_matches == 0).sum()),
        "pattern_rows_matching_1": int((n_matches == 1).sum()),
        "pattern_rows_matching_gt1": int((n_matches > 1).sum()),
        "matched_pattern_rows": int(matched.sum()),
        "pattern_to_transaction_match_rate": (float(matched.mean()) if n_patterns else None),
        "laundering_txns_total": int(len(laund)),
        "laundering_txns_not_in_any_pattern": int((~laund_matched).sum()),
    }
