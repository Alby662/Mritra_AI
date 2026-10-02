"""Dense-day sensitivity analysis (PREREGISTRATION.md §9 Deviations, 2026-10-02).

The full pre-registered test set is the primary analysis and is never truncated. This
module adds an EVALUATION-side mask only: test rows on days whose total transaction count
(across the whole dataset, all splits) meets ``eval.dense_min_daily_txns``
(``configs/experiment.yaml``, default 10,000). Features and graph history for those rows
are computed from the full, untruncated data exactly as for every other row -- only which
rows the *sensitivity* metrics are scored on changes. Added after seeing the sparse,
heavily laundering-skewed tail in per-day label rates (DECISIONS.md), before any C1/C3/C4
model results.

"Dense" is a property of the whole dataset's daily volume (every split), computed once by
``scripts/prepare_data.py`` into ``results/data_stats.json: txns_per_day`` -- reused here
rather than recomputed from a multi-split DataFrame that evaluation code wouldn't
otherwise need to carry around.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def dense_day_min_txns() -> int:
    from mritra.config import load_config

    return int(load_config()["eval"]["dense_min_daily_txns"])


def dense_days_from_data_stats(
    data_stats: dict[str, Any] | None = None,
    min_daily_txns: int | None = None,
) -> set[str]:
    """Dates (ISO, e.g. "2022-09-03") whose total txn count (all splits) meets the
    threshold, per ``results/data_stats.json: txns_per_day``."""
    if min_daily_txns is None:
        min_daily_txns = dense_day_min_txns()
    if data_stats is None:
        from mritra.config import repo_path

        with (repo_path("results") / "data_stats.json").open(encoding="utf-8") as f:
            data_stats = json.load(f)

    return {
        date
        for date, counts in data_stats["txns_per_day"].items()
        if counts["total"] >= min_daily_txns
    }


def dense_day_mask(
    test_df: pd.DataFrame,
    dense_days: set[str] | None = None,
    ts_col: str = "ts",
) -> pd.Series:
    """True for rows of ``test_df`` (already filtered to the test split) whose day is
    in ``dense_days``."""
    if dense_days is None:
        dense_days = dense_days_from_data_stats()
    day = pd.to_datetime(test_df[ts_col], unit="s", utc=True).dt.date.astype(str)
    return day.isin(dense_days)


def evaluate_with_sensitivity(
    test_df: pd.DataFrame,
    evaluate_fn: Any,
    dense_days: set[str] | None = None,
    **evaluate_kwargs: Any,
) -> dict[str, Any]:
    """Run ``evaluate_fn`` (e.g. ``mritra.eval.metrics.evaluate_configuration``) twice on
    test-period data: once on the full test set (primary, unchanged) and once on the
    dense-day-masked subset (sensitivity), clearly labelled.

    Parameters
    ----------
    test_df : DataFrame
        Test-period rows only, with the columns ``evaluate_fn`` needs plus ``ts``.
    evaluate_fn : callable
        Called as ``evaluate_fn(subset_df, **evaluate_kwargs)``.
    """
    mask = dense_day_mask(test_df, dense_days)
    return {
        "primary": evaluate_fn(test_df, **evaluate_kwargs),
        "sensitivity_dense_days": evaluate_fn(test_df[mask], **evaluate_kwargs),
        "sensitivity_rows_kept": int(mask.sum()),
        "sensitivity_rows_total": int(len(test_df)),
    }
