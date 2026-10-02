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
    df: pd.DataFrame,
    n_raw: int,
    dup_stats: DuplicateStats,
    drop_exact_duplicates: bool,
    patterns: pd.DataFrame,
) -> dict:
    accounts = pd.concat(
        [
            df[["from_bank", "from_acct"]].set_axis(["bank", "acct"], axis=1),
            df[["to_bank", "to_acct"]].set_axis(["bank", "acct"], axis=1),
        ]
    ).astype({"acct": "string"})
    splits = {}
    split_max_ts = {}
    for name in SPLITS:
        part = df[df["split"] == name]
        splits[name] = {
            "rows": len(part),
            "first_ts": iso(part["ts"].min()),
            "last_ts": iso(part["ts"].max()),
            "laundering_txns": int(part["is_laund"].sum()),
            "laundering_rate": float(part["is_laund"].mean()),
        }
        split_max_ts[name] = int(part["ts"].max())

    day = pd.to_datetime(df["ts"], unit="s", utc=True).dt.floor("D")
    txns_per_day = {
        d.date().isoformat(): int(c) for d, c in day.value_counts().sort_index().items()
    }

    # A pattern straddles a split boundary if its earliest and latest transaction fall in
    # different splits. Split membership for any timestamp is determined the same way
    # temporal_split assigns it (<=  train's last ts -> train, <= val's last ts -> val,
    # else test), so this does not require joining patterns to the trans table by row_id.
    def ts_to_split(ts: int) -> str:
        if ts <= split_max_ts["train"]:
            return "train"
        if ts <= split_max_ts["val"]:
            return "val"
        return "test"

    pattern_span = patterns.groupby("pattern_id", observed=True)["ts"].agg(["min", "max"])
    pattern_span["first_split"] = pattern_span["min"].map(ts_to_split)
    pattern_span["last_split"] = pattern_span["max"].map(ts_to_split)
    patterns_straddling_split = int(
        (pattern_span["first_split"] != pattern_span["last_split"]).sum()
    )

    return {
        "rows_raw": n_raw,
        "rows_loaded": len(df),  # after the drop below, if any
        "drop_exact_duplicates": drop_exact_duplicates,  # configs/experiment.yaml: data.*
        "duplicate_rows": dup_stats.duplicate_rows,  # always computed, regardless of the flag
        "duplicate_rows_is_laund": dup_stats.duplicate_rows_is_laund,
        "distinct_banks": int(pd.concat([df["from_bank"], df["to_bank"]]).nunique()),
        "distinct_accounts": int(len(accounts.drop_duplicates())),
        "laundering_txns": int(df["is_laund"].sum()),
        "laundering_rate": float(df["is_laund"].mean()),
        "first_ts": iso(df["ts"].min()),
        "last_ts": iso(df["ts"].max()),
        "splits": splits,
        "txns_per_day": txns_per_day,
        "patterns_straddling_split": patterns_straddling_split,
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

    drop_exact_duplicates = cfg["data"]["drop_exact_duplicates"]
    df, n_raw, dup_stats = read_transactions(
        raw / files["trans"], fmt, drop_exact_duplicates=drop_exact_duplicates
    )
    df["split"] = temporal_split(df["ts"], cfg["split"]["train"], cfg["split"]["val"])
    df.to_parquet(out / "trans.parquet", index=False)

    patterns = parse_patterns(raw / files["patterns"], fmt)
    patterns.to_parquet(out / "patterns.parquet", index=False)

    stats = data_stats(df, n_raw, dup_stats, drop_exact_duplicates, patterns)
    (results / "data_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("wrote %s and %s", out, results / "data_stats.json")
    if dup_stats.duplicate_rows:
        logger.info(
            "%d exact-duplicate rows found (%d with is_laund=1); drop_exact_duplicates=%s",
            dup_stats.duplicate_rows,
            dup_stats.duplicate_rows_is_laund,
            drop_exact_duplicates,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
