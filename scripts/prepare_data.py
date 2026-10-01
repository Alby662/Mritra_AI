"""Convert raw HI-Small files to Parquet and write results/data_stats.json."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import pandas as pd

from mritra.config import config_sha256, load_config, repo_path
from mritra.data.load import DuplicateStats, read_transactions
from mritra.data.patterns import parse_patterns
from mritra.data.split import SPLITS, temporal_split

logger = logging.getLogger("prepare_data")


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=UTC).isoformat()


def data_stats(
    df: pd.DataFrame, n_raw: int, dup_stats: DuplicateStats, patterns: pd.DataFrame
) -> dict:
    accounts = pd.concat(
        [
            df[["from_bank", "from_acct"]].set_axis(["bank", "acct"], axis=1),
            df[["to_bank", "to_acct"]].set_axis(["bank", "acct"], axis=1),
        ]
    ).astype({"acct": "string"})
    splits = {}
    for name in SPLITS:
        part = df[df["split"] == name]
        splits[name] = {
            "rows": len(part),
            "first_ts": iso(part["ts"].min()),
            "last_ts": iso(part["ts"].max()),
            "laundering_rate": float(part["is_laund"].mean()),
        }
    return {
        "rows_raw": n_raw,
        "rows_loaded": len(df),  # nothing dropped; see duplicate_rows below
        "duplicate_rows": dup_stats.duplicate_rows,
        "duplicate_rows_is_laund": dup_stats.duplicate_rows_is_laund,
        "duplicate_rows_note": (
            "Exact-duplicate rows found but NOT dropped (PREREGISTRATION.md §3 says to "
            "drop; not yet reconciled — see DECISIONS.md). Decide before prereg-v1."
        ),
        "distinct_banks": int(pd.concat([df["from_bank"], df["to_bank"]]).nunique()),
        "distinct_accounts": int(len(accounts.drop_duplicates())),
        "laundering_txns": int(df["is_laund"].sum()),
        "laundering_rate": float(df["is_laund"].mean()),
        "first_ts": iso(df["ts"].min()),
        "last_ts": iso(df["ts"].max()),
        "splits": splits,
        "payment_formats": {str(k): int(v) for k, v in df["fmt"].value_counts().items()},
        "currencies_paid": {str(k): int(v) for k, v in df["cur_paid"].value_counts().items()},
        "patterns": int(patterns["pattern_id"].nunique()),
        "pattern_txns": len(patterns),
        "pattern_types": {
            str(k): int(v)
            for k, v in patterns.groupby("pattern_type", observed=True)["pattern_id"]
            .nunique()
            .items()
        },
        "config_sha256": config_sha256(),
    }


def main() -> None:
    cfg = load_config()
    files, fmt = cfg["dataset"]["files"], cfg["dataset"]["timestamp_format"]
    raw = repo_path(cfg["paths"]["raw"])
    out = repo_path(cfg["paths"]["parquet"])
    results = repo_path(cfg["paths"]["results"])
    out.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    df, n_raw, dup_stats = read_transactions(raw / files["trans"], fmt)
    df["split"] = temporal_split(df["ts"], cfg["split"]["train"], cfg["split"]["val"])
    df.to_parquet(out / "trans.parquet", index=False)

    patterns = parse_patterns(raw / files["patterns"], fmt)
    patterns.to_parquet(out / "patterns.parquet", index=False)

    stats = data_stats(df, n_raw, dup_stats, patterns)
    (results / "data_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("wrote %s and %s", out, results / "data_stats.json")
    if dup_stats.duplicate_rows:
        logger.warning(
            "STOP: %d exact-duplicate rows found (%d with is_laund=1) — not dropped. "
            "Reconcile with PREREGISTRATION.md §3 before tagging prereg-v1.",
            dup_stats.duplicate_rows,
            dup_stats.duplicate_rows_is_laund,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
