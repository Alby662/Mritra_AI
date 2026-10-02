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
    n_undefined: int = 0
    undefined_share: float = 0.0


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


def _default_gap_eps() -> float:
    from mritra.config import load_config

    return float(load_config()["gates"]["min_gap_f1"])


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
    eps: float | None = None,
) -> BootstrapCI:
    """Bootstrap CI for G = (F1_C3 - F1_C1) / (F1_C4 - F1_C1).

    A resample (or the original sample) is "undefined" when
    ``|F1_C4 - F1_C1| < eps`` -- the oracle has no meaningful advantage over
    the siloed model there, so the ratio is not a meaningful gap, just a
    division by a near-zero number (PREREGISTRATION.md §6.2: "If F1_C4 -
    F1_C1 <= 0.01, G is reported as 'undefined (no gap)'"). ``eps`` defaults
    to that same ``configs/experiment.yaml: gates.min_gap_f1``.

    If the *original* (non-resampled) sample is undefined, the whole result
    is undefined: ``point_estimate``, ``ci_lower`` and ``ci_upper`` are all
    NaN, rather than reporting a CI built only from the lucky minority of
    resamples that happened not to be degenerate. ``n_undefined`` /
    ``undefined_share`` always report how many of the ``n_resamples`` were
    individually undefined, which can be nonzero even when the original
    sample is well-defined (resampling can land on a degenerate draw by
    chance, especially with few positives).
    """
    if eps is None:
        eps = _default_gap_eps()

    def resample_f1s(idx: np.ndarray) -> tuple[float, float, float] | None:
        yt = y_true[idx]
        if yt.sum() == 0 or yt.sum() == len(yt):
            return None
        f1_c1 = f1_score(
            yt, (y_prob_c1[idx] >= threshold_c1).astype(int), pos_label=1, zero_division=0.0
        )
        f1_c3 = f1_score(
            yt, (y_prob_c3[idx] >= threshold_c3).astype(int), pos_label=1, zero_division=0.0
        )
        f1_c4 = f1_score(
            yt, (y_prob_c4[idx] >= threshold_c4).astype(int), pos_label=1, zero_division=0.0
        )
        return f1_c1, f1_c3, f1_c4

    n = len(y_true)
    orig_f1s = resample_f1s(np.arange(n))
    orig_gap = None
    if orig_f1s is not None:
        f1_c1, f1_c3, f1_c4 = orig_f1s
        orig_gap = (f1_c3 - f1_c1) / (f1_c4 - f1_c1) if abs(f1_c4 - f1_c1) >= eps else None

    rng = np.random.default_rng(seed)
    gaps = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        f1s = resample_f1s(idx)
        if f1s is None:
            gaps[i] = np.nan
            continue
        f1_c1, f1_c3, f1_c4 = f1s
        denom = f1_c4 - f1_c1
        gaps[i] = (f1_c3 - f1_c1) / denom if abs(denom) >= eps else np.nan

    n_undefined = int(np.isnan(gaps).sum())
    undefined_share = n_undefined / n_resamples
    valid = gaps[~np.isnan(gaps)]

    if orig_gap is None:
        return BootstrapCI(
            metric="gap_recovered",
            point_estimate=float("nan"),
            ci_lower=float("nan"),
            ci_upper=float("nan"),
            ci_level=ci_level,
            n_resamples=n_resamples,
            n_undefined=n_undefined,
            undefined_share=undefined_share,
        )

    if len(valid) == 0:
        # Original sample is defined but every single resample was degenerate (possible
        # with very few positives). The point estimate is still the original statistic;
        # there just isn't bootstrap data to bound a CI around it.
        return BootstrapCI(
            metric="gap_recovered",
            point_estimate=float(orig_gap),
            ci_lower=float("nan"),
            ci_upper=float("nan"),
            ci_level=ci_level,
            n_resamples=n_resamples,
            n_undefined=n_undefined,
            undefined_share=undefined_share,
        )

    alpha = (1 - ci_level) / 2
    return BootstrapCI(
        metric="gap_recovered",
        point_estimate=float(orig_gap),
        ci_lower=float(np.percentile(valid, 100 * alpha)),
        ci_upper=float(np.percentile(valid, 100 * (1 - alpha))),
        ci_level=ci_level,
        n_resamples=n_resamples,
        n_undefined=n_undefined,
        undefined_share=undefined_share,
    )
