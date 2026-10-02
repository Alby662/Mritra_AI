"""Hand-computed checks for mritra/eval/metrics.py and mritra/eval/bootstrap.py.

These cover the code that produces the headline F1 / PR-AUC / G numbers
(CLAUDE.md §6: "Metrics: test against a hand-computed toy example").
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mritra.data.partition import add_institutions
from mritra.eval.bootstrap import bootstrap_gap_recovered, bootstrap_metric_diff
from mritra.eval.metrics import compute_subset_metrics, evaluate_configuration, gap_recovered


def test_f1_hand_computed() -> None:
    # TP=3 (idx 0,4,7), FP=1 (idx 3), FN=1 (idx 1), TN=3 (idx 2,5,6).
    # precision = 3/4 = 0.75, recall = 3/4 = 0.75, F1 = 2*.75*.75/1.5 = 0.75
    y_true = np.array([1, 1, 0, 0, 1, 0, 0, 1])
    y_pred = np.array([1, 0, 0, 1, 1, 0, 0, 1])
    y_prob = y_pred.astype(float)
    m = compute_subset_metrics(y_true, y_pred, y_prob, "all")
    assert m.f1_minority == 0.75
    assert m.n_samples == 8
    assert m.n_positive == 4


def test_pr_auc_hand_computed() -> None:
    # Sorted by score desc: 0.8(label1), 0.4(label0), 0.35(label1), 0.1(label0).
    # R=1/2,P=1/1 at rank1; R=1,P=2/3 at rank3 (only positive-label ranks count).
    # AP = (0.5-0)*1 + (1-0.5)*(2/3) = 0.5 + 1/3 = 5/6
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.4, 0.35, 0.8])
    y_pred = (y_prob >= 0.5).astype(int)
    m = compute_subset_metrics(y_true, y_pred, y_prob, "all")
    assert abs(m.pr_auc - 5 / 6) < 1e-9


def test_subset_metrics_empty_or_no_positives_is_zero_not_error() -> None:
    assert compute_subset_metrics(np.array([]), np.array([]), np.array([]), "x").f1_minority == 0.0
    y_true = np.zeros(5)
    y_pred = np.zeros(5)
    y_prob = np.zeros(5)
    m = compute_subset_metrics(y_true, y_pred, y_prob, "x")
    assert m.f1_minority == 0.0
    assert m.pr_auc == 0.0


def test_gap_recovered_hand_computed() -> None:
    # G = (0.6-0.4)/(0.8-0.4) = 0.2/0.4 = 0.5
    assert abs(gap_recovered(f1_c1=0.4, f1_c3=0.6, f1_c4=0.8) - 0.5) < 1e-9


def test_gap_recovered_zero_denominator_returns_none() -> None:
    # F1_C4 == F1_C1: oracle has no advantage over siloed, G is undefined, not a ZeroDivisionError.
    assert gap_recovered(f1_c1=0.5, f1_c3=0.9, f1_c4=0.5) is None
    assert gap_recovered(f1_c1=0.5, f1_c3=0.1, f1_c4=0.5) is None


def test_evaluate_configuration_subsets_match_toy_partition() -> None:
    # Two institutions: banks {0, 1} -> inst 0, banks {2, 3} -> inst 1.
    inst_of = {0: 0, 1: 0, 2: 1, 3: 1}
    df = pd.DataFrame(
        {
            "from_bank": [0, 0, 2, 1],
            "to_bank": [1, 2, 3, 3],
            "is_laund": [1, 1, 0, 1],
            "prob": [0.9, 0.8, 0.2, 0.7],
            "pred": [1, 1, 0, 1],
        }
    )
    tagged = add_institutions(df, inst_of)
    # row0: inst0->inst0 (within); row1: inst0->inst1 (cross);
    # row2: inst1->inst1 (within); row3: inst0->inst1 (cross)
    assert tagged["cross"].tolist() == [False, True, False, True]

    results = evaluate_configuration(tagged)
    assert results["all"].n_samples == 4
    assert results["cross_bank"].n_samples == 2
    assert results["within_bank"].n_samples == 2
    # cross subset is rows 1,3: both is_laund=1, both pred=1 -> F1 = 1.0
    assert results["cross_bank"].f1_minority == 1.0
    # within subset is rows 0,2: is_laund=[1,0], pred=[1,0] -> perfect -> F1 = 1.0
    assert results["within_bank"].f1_minority == 1.0


def test_bootstrap_fixed_seed_gives_identical_ci() -> None:
    rng = np.random.default_rng(0)
    n = 200
    y_true = rng.integers(0, 2, size=n)
    y_prob_a = rng.random(n)
    y_prob_b = rng.random(n)

    a = bootstrap_metric_diff(y_true, y_prob_a, y_prob_b, 0.5, 0.5, "f1", n_resamples=50, seed=7)
    b = bootstrap_metric_diff(y_true, y_prob_a, y_prob_b, 0.5, 0.5, "f1", n_resamples=50, seed=7)
    assert a == b


def test_bootstrap_identical_predictions_ci_is_zero() -> None:
    rng = np.random.default_rng(1)
    n = 200
    y_true = rng.integers(0, 2, size=n)
    y_prob = rng.random(n)

    result = bootstrap_metric_diff(y_true, y_prob, y_prob, 0.5, 0.5, "f1", n_resamples=100, seed=3)
    assert result.point_estimate == 0.0
    assert result.ci_lower == 0.0
    assert result.ci_upper == 0.0


def test_bootstrap_gap_recovered_identical_configs_is_zero() -> None:
    # C1 == C3 == C4: every resample has a non-zero denominator (unless degenerate) and
    # the gap must be exactly 0 every time -> CI is a point mass at 0.
    rng = np.random.default_rng(2)
    n = 300
    y_true = rng.integers(0, 2, size=n)
    y_prob = rng.random(n)

    result = bootstrap_gap_recovered(
        y_true, y_prob, y_prob, y_prob, 0.5, 0.5, 0.5, n_resamples=100, seed=5
    )
    assert result.point_estimate == 0.0
    assert result.ci_lower == 0.0
    assert result.ci_upper == 0.0
