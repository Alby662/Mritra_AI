"""Dense-day sensitivity analysis (PREREGISTRATION.md §9 Deviations, 2026-10-02)."""

from __future__ import annotations

import pandas as pd

from mritra.eval.sensitivity import (
    dense_day_mask,
    dense_days_from_data_stats,
    evaluate_with_sensitivity,
)


def _toy_data_stats() -> dict:
    return {
        "txns_per_day": {
            "1970-01-01": {"total": 12_000, "laundering": 50, "non_laundering": 11_950},
            "1970-01-02": {"total": 500, "laundering": 20, "non_laundering": 480},
        }
    }


def _toy_test_df() -> pd.DataFrame:
    day1 = 0  # 1970-01-01 (dense in _toy_data_stats)
    day2 = 86_400  # 1970-01-02 (sparse)
    rows = [
        {"ts": day1, "is_laund": 1},
        {"ts": day1 + 100, "is_laund": 0},
        {"ts": day2, "is_laund": 0},
    ]
    return pd.DataFrame(rows)


def test_dense_days_from_data_stats_applies_threshold() -> None:
    stats = _toy_data_stats()
    assert dense_days_from_data_stats(stats, min_daily_txns=10_000) == {"1970-01-01"}
    assert dense_days_from_data_stats(stats, min_daily_txns=100) == {
        "1970-01-01",
        "1970-01-02",
    }


def test_dense_day_mask_marks_only_rows_on_dense_days() -> None:
    df = _toy_test_df()
    dense_days = dense_days_from_data_stats(_toy_data_stats(), min_daily_txns=10_000)
    mask = dense_day_mask(df, dense_days)
    expected = pd.Series([True, True, False], index=df.index)
    pd.testing.assert_series_equal(mask, expected, check_names=False)


def test_evaluate_with_sensitivity_labels_primary_and_sensitivity_separately() -> None:
    df = _toy_test_df()
    dense_days = dense_days_from_data_stats(_toy_data_stats(), min_daily_txns=10_000)

    def fake_evaluate(subset: pd.DataFrame) -> dict:
        return {"n": len(subset), "n_laund": int(subset["is_laund"].sum())}

    result = evaluate_with_sensitivity(df, fake_evaluate, dense_days=dense_days)

    assert result["primary"] == fake_evaluate(df)
    assert result["primary"] == {"n": 3, "n_laund": 1}
    assert result["sensitivity_rows_total"] == 3
    assert result["sensitivity_rows_kept"] == 2  # day1's 2 rows only
    assert result["sensitivity_dense_days"] == {"n": 2, "n_laund": 1}
