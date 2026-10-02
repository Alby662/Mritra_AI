"""1,000-sample bootstrap 95% CI on the C3 − C1 difference (plan §10).

Pre-registered claim: "G > 0 with a bootstrap interval excluding 0 on
cross-bank laundering, under both partitions."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, f1_score

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapCI:
    """Bootstrap confidence interval for a metric difference."""

    metric: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    ci_level: float
    n_resamples: int


def bootstrap_metric_diff(
    y_true: np.ndarray,
    y_prob_a: np.ndarray,
    y_prob_b: np.ndarray,
    threshold_a: float,
    threshold_b: float,
    metric: str = "f1",
    n_resamples: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> BootstrapCI:
    """Bootstrap CI for the difference in a metric between two systems (B − A).

    Parameters
    ----------
    y_true : ground truth labels
    y_prob_a, y_prob_b : predicted probabilities from systems A and B
    threshold_a, threshold_b : classification thresholds
    metric : "f1" or "pr_auc"
    n_resamples : number of bootstrap samples
    ci_level : confidence level (e.g. 0.95)
    seed : random seed

    Returns
    -------
    BootstrapCI with point estimate and confidence interval.
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    diffs = np.empty(n_resamples, dtype=np.float64)

    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        pa = y_prob_a[idx]
        pb = y_prob_b[idx]

        if yt.sum() == 0 or yt.sum() == len(yt):
            diffs[i] = 0.0
            continue

        if metric == "f1":
            pred_a = (pa >= threshold_a).astype(int)
            pred_b = (pb >= threshold_b).astype(int)
            score_a = f1_score(yt, pred_a, pos_label=1, zero_division=0.0)
            score_b = f1_score(yt, pred_b, pos_label=1, zero_division=0.0)
        elif metric == "pr_auc":
            score_a = average_precision_score(yt, pa)
            score_b = average_precision_score(yt, pb)
        else:
            raise ValueError(f"Unknown metric: {metric}")

        diffs[i] = score_b - score_a

    alpha = (1 - ci_level) / 2
    ci_lower = float(np.percentile(diffs, 100 * alpha))
    ci_upper = float(np.percentile(diffs, 100 * (1 - alpha)))
    point = float(np.mean(diffs))

    return BootstrapCI(
        metric=metric,
        point_estimate=point,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_level=ci_level,
        n_resamples=n_resamples,
    )


def bootstrap_gap_recovered(
    y_true: np.ndarray,
    y_prob_c1: np.ndarray,
    y_prob_c3: np.ndarray,
    y_prob_c4: np.ndarray,
    threshold_c1: float,
    threshold_c3: float,
    threshold_c4: float,
    n_resamples: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> BootstrapCI:
    """Bootstrap CI for G = (F1_C3 - F1_C1) / (F1_C4 - F1_C1)."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    gaps = np.empty(n_resamples, dtype=np.float64)

    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]

        if yt.sum() == 0 or yt.sum() == len(yt):
            gaps[i] = np.nan
            continue

        f1_c1 = f1_score(
            yt, (y_prob_c1[idx] >= threshold_c1).astype(int), pos_label=1, zero_division=0.0
        )
        f1_c3 = f1_score(
            yt, (y_prob_c3[idx] >= threshold_c3).astype(int), pos_label=1, zero_division=0.0
        )
        f1_c4 = f1_score(
            yt, (y_prob_c4[idx] >= threshold_c4).astype(int), pos_label=1, zero_division=0.0
        )

        denom = f1_c4 - f1_c1
        if abs(denom) < 1e-10:
            gaps[i] = np.nan
        else:
            gaps[i] = (f1_c3 - f1_c1) / denom

    valid = gaps[~np.isnan(gaps)]
    if len(valid) == 0:
        return BootstrapCI(
            metric="gap_recovered",
            point_estimate=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            ci_level=ci_level,
            n_resamples=n_resamples,
        )

    alpha = (1 - ci_level) / 2
    return BootstrapCI(
        metric="gap_recovered",
        point_estimate=float(np.mean(valid)),
        ci_lower=float(np.percentile(valid, 100 * alpha)),
        ci_upper=float(np.percentile(valid, 100 * (1 - alpha))),
        ci_level=ci_level,
        n_resamples=n_resamples,
    )
