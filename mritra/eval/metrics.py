"""Evaluation metrics (plan §10).

Test period only.  **Never report accuracy.**

Metrics:
  - Minority-class F1 (on laundering txns; subsets: all / cross / within)
  - PR-AUC (average precision on same subsets)
  - Gap recovered G = (F1_C3 - F1_C1) / (F1_C4 - F1_C1)
  - Innocent money flagged
  - Coverage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubsetMetrics:
    """Metrics for one subset (all / cross_bank / within_bank)."""

    subset: str
    n_samples: int
    n_positive: int
    f1_minority: float
    pr_auc: float


def compute_subset_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    subset_name: str,
) -> SubsetMetrics:
    """Compute F1 and PR-AUC on a single subset."""
    n = len(y_true)
    n_pos = int(y_true.sum())

    if n == 0 or n_pos == 0:
        return SubsetMetrics(
            subset=subset_name,
            n_samples=n,
            n_positive=n_pos,
            f1_minority=0.0,
            pr_auc=0.0,
        )

    f1 = f1_score(y_true, y_pred, pos_label=1, zero_division=0.0)
    pr_auc = average_precision_score(y_true, y_prob)

    return SubsetMetrics(
        subset=subset_name,
        n_samples=n,
        n_positive=n_pos,
        f1_minority=float(f1),
        pr_auc=float(pr_auc),
    )


def evaluate_configuration(
    df: pd.DataFrame,
    prob_col: str = "prob",
    pred_col: str = "pred",
    label_col: str = "is_laund",
    cross_col: str = "cross",
) -> dict[str, SubsetMetrics]:
    """Compute metrics on all three subsets for one configuration.

    Parameters
    ----------
    df : DataFrame
        Test-period data with prob, pred, is_laund, and cross columns.

    Returns
    -------
    dict mapping subset name to SubsetMetrics.
    """
    results = {}
    y_true = df[label_col].to_numpy()
    y_pred = df[pred_col].to_numpy()
    y_prob = df[prob_col].to_numpy()

    results["all"] = compute_subset_metrics(y_true, y_pred, y_prob, "all")

    cross_mask = df[cross_col].to_numpy().astype(bool)
    results["cross_bank"] = compute_subset_metrics(
        y_true[cross_mask], y_pred[cross_mask], y_prob[cross_mask], "cross_bank"
    )
    results["within_bank"] = compute_subset_metrics(
        y_true[~cross_mask], y_pred[~cross_mask], y_prob[~cross_mask], "within_bank"
    )

    return results


def gap_recovered(f1_c1: float, f1_c3: float, f1_c4: float) -> float | None:
    """Compute G = (F1_C3 - F1_C1) / (F1_C4 - F1_C1).

    Returns None if the denominator is zero (oracle = siloed).
    """
    denom = f1_c4 - f1_c1
    if abs(denom) < 1e-10:
        return None
    return (f1_c3 - f1_c1) / denom


def innocent_money_flagged(
    df: pd.DataFrame,
    pred_col: str = "pred",
    label_col: str = "is_laund",
    amount_col: str = "amt_paid",
) -> dict[str, Any]:
    """Sum of legitimate transaction amounts flagged; # accounts flagged with no involvement."""
    flagged = df[df[pred_col] == 1]
    legit_flagged = flagged[flagged[label_col] == 0]

    # Accounts with no laundering involvement that were flagged
    acct_laund = df.groupby(["from_inst", "from_acct"], observed=True)[label_col].max()
    clean_accts = set(acct_laund[acct_laund == 0].index)

    flagged_accts = set(
        zip(flagged["from_inst"], flagged["from_acct"], strict=True)
    )
    innocent_flagged = flagged_accts & clean_accts

    return {
        "legit_amount_flagged": float(legit_flagged[amount_col].sum()),
        "legit_txns_flagged": len(legit_flagged),
        "innocent_accounts_flagged": len(innocent_flagged),
        "total_accounts_flagged": len(flagged_accts),
    }


def coverage(
    df: pd.DataFrame,
    pred_col: str = "pred",
    amount_col: str = "amt_paid",
) -> dict[str, float]:
    """Share of transaction volume visible to the detector."""
    total_vol = df[amount_col].sum()
    scored_vol = df[df[pred_col].notna()][amount_col].sum()
    return {
        "total_volume": float(total_vol),
        "scored_volume": float(scored_vol),
        "coverage_share": float(scored_vol / total_vol) if total_vol > 0 else 0.0,
    }
