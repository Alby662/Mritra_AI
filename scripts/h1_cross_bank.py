"""H1: how much laundering crosses institutions under P1 and P2 -> results/h1.json."""

from __future__ import annotations

import json
import logging

import pandas as pd

from mritra.config import config_sha256, load_config, repo_path
from mritra.data.load import COLUMNS
from mritra.data.partition import add_institutions, bank_volumes, make_partition
from mritra.data.patterns import (
    MATCH_KEY_COLUMNS,
    match_patterns_to_transactions,
    pattern_cross_share,
)

logger = logging.getLogger("h1_cross_bank")

# PREREGISTRATION.md §4, verbatim: "Cross-bank pattern | A laundering attempt in the
# Patterns file whose transactions touch > 1 institution". That is the PRIMARY variant
# below (`cross_share_patterns`, `n_inst > 1`); the H1 gate is evaluated against it.
# `cross_share_patterns_any_edge` is a SECONDARY variant prereg does not define — see
# mritra/data/patterns.py:pattern_cross_share docstring — reported for comparison only.


def h1_for_partition(
    df: pd.DataFrame, patterns: pd.DataFrame, inst_of: dict[int, int], k: int
) -> dict:
    tagged = add_institutions(df, inst_of)
    per_inst = pd.concat([tagged["from_inst"], tagged["to_inst"]]).value_counts()
    per_inst = per_inst.reindex(range(k), fill_value=0)
    laund = tagged[tagged["is_laund"] == 1]
    per_pattern = pattern_cross_share(patterns, inst_of)
    by_type = per_pattern.groupby("pattern_type", observed=True)[["cross", "cross_any_edge"]].agg(
        ["mean", "size"]
    )
    return {
        "bank_to_institution": {str(b): i for b, i in sorted(inst_of.items())},
        "txn_appearances_per_institution": [int(v) for v in per_inst],
        "cross_share_all_txns": float(tagged["cross"].mean()),
        "cross_share_laundering_txns": float(laund["cross"].mean()),
        "cross_share_patterns": float(per_pattern["cross"].mean()),  # PRIMARY (prereg §4)
        "cross_share_patterns_any_edge": float(per_pattern["cross_any_edge"].mean()),  # SECONDARY
        "cross_share_patterns_by_type": {
            str(t): {
                "share_primary": float(r[("cross", "mean")]),
                "share_any_edge": float(r[("cross_any_edge", "mean")]),
                "n": int(r[("cross", "size")]),
            }
            for t, r in by_type.iterrows()
        },
    }


def main() -> None:
    cfg = load_config()
    k = cfg["institutions"]["k"]
    parquet = repo_path(cfg["paths"]["parquet"])
    results = repo_path(cfg["paths"]["results"])

    trans_cols = sorted(set(MATCH_KEY_COLUMNS) | {"from_bank", "to_bank", "is_laund"})
    df = pd.read_parquet(parquet / "trans.parquet", columns=trans_cols)
    pattern_cols = ["pattern_id", "pattern_type", *COLUMNS]
    patterns = pd.read_parquet(parquet / "patterns.parquet", columns=pattern_cols)
    missing = set(pd.concat([patterns["from_bank"], patterns["to_bank"]])) - set(
        bank_volumes(df).index
    )
    if missing:
        examples = sorted(missing)[:5]
        raise ValueError(f"{len(missing)} pattern banks not in transactions, e.g. {examples}")

    out: dict = {
        "k": k,
        "config_sha256": config_sha256(),
        "match": match_patterns_to_transactions(df, patterns),
        "partitions": {},
    }
    logger.info(
        "pattern->transaction match rate = %.4f (%d/%d); laundering txns not in any pattern = %d",
        out["match"]["pattern_to_transaction_match_rate"] or 0.0,
        out["match"]["matched_pattern_rows"],
        out["match"]["pattern_rows"],
        out["match"]["laundering_txns_not_in_any_pattern"],
    )

    for name, p in cfg["partitions"].items():
        inst_of = make_partition(df, p["method"], k, p.get("seed"))
        out["partitions"][name] = h1_for_partition(df, patterns, inst_of, k)
        logger.info(
            "%s cross-bank pattern share: primary=%.3f any_edge=%.3f",
            name,
            out["partitions"][name]["cross_share_patterns"],
            out["partitions"][name]["cross_share_patterns_any_edge"],
        )

    gate = cfg["gates"]["h1_min_cross_pattern_share"]
    out["gate_threshold"] = gate
    out["gate_definition"] = (
        "primary (PREREGISTRATION.md §4): share of patterns touching > 1 institution"
    )
    out["gate_passed_P1"] = out["partitions"]["P1"]["cross_share_patterns"] >= gate
    results.mkdir(parents=True, exist_ok=True)
    (results / "h1.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    logger.info("H1 gate (P1 >= %.2f): %s", gate, "PASS" if out["gate_passed_P1"] else "FAIL")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
