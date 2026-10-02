"""scripts/run_eval.py: C1 cross-bank scoring (PREREGISTRATION §5), hand-computed."""

from __future__ import annotations

import pandas as pd

from scripts.run_eval import evaluate_c1_cross_bank


def test_c1_cross_bank_takes_max_of_two_institutions_hand_computed() -> None:
    # Institution 0's own model vs institution 1's own model score the SAME two
    # cross-bank transactions differently; C1's cross-bank score is the max of the two.
    #   row 1: max(0.9, 0.2) = 0.9 (laundering)
    #   row 2: max(0.1, 0.8) = 0.8 (not laundering)
    # These two probs perfectly separate the labels (0.9 > 0.8), so there exists a
    # threshold in (0.8, 0.9] giving TP=1, FP=0, FN=0 -> F1=1.0, PR-AUC=1.0.
    scores_by_inst = {
        0: pd.DataFrame({"row_id": [1, 2], "prob": [0.9, 0.1]}),
        1: pd.DataFrame({"row_id": [1, 2], "prob": [0.2, 0.8]}),
    }
    cross_txns = pd.DataFrame({"row_id": [1, 2], "from_inst": [0, 0], "to_inst": [1, 1]})
    y_true = pd.Series({1: 1, 2: 0})

    result = evaluate_c1_cross_bank(scores_by_inst, cross_txns, y_true)

    assert result["n_samples"] == 2
    assert result["n_positive"] == 1
    assert 0.8 < result["threshold"] <= 0.9
    assert result["f1_minority"] == 1.0
    assert result["pr_auc"] == 1.0


def test_c1_cross_bank_missing_institution_score_defaults_to_zero() -> None:
    # Institution 1 never scored row 2 at all (e.g. it wasn't in that institution's
    # feature table) -- cross_bank_max_score treats a missing score as 0.0, so the max
    # is just institution 0's own score.
    scores_by_inst = {
        0: pd.DataFrame({"row_id": [1, 2], "prob": [0.7, 0.3]}),
        1: pd.DataFrame({"row_id": [1], "prob": [0.1]}),  # row 2 missing
    }
    cross_txns = pd.DataFrame({"row_id": [1, 2], "from_inst": [0, 0], "to_inst": [1, 1]})
    y_true = pd.Series({1: 1, 2: 0})

    result = evaluate_c1_cross_bank(scores_by_inst, cross_txns, y_true)
    assert result["n_samples"] == 2


def test_c1_cross_bank_empty_cross_txns_reports_zero_samples() -> None:
    result = evaluate_c1_cross_bank(
        {}, pd.DataFrame(columns=["row_id", "from_inst", "to_inst"]), pd.Series(dtype=int)
    )
    assert result == {"n_samples": 0, "n_positive": 0, "f1_minority": 0.0, "pr_auc": 0.0}
