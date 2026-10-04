"""Scoring and inference utilities (plan §7.2).

Account score = max of its transaction scores. Supports both LightGBM
(standard) and Snap ML Booster (LinuxONE z16 accelerator).
"""

from __future__ import annotations

import logging
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def score_transactions(
    model: lgb.LGBMClassifier | lgb.Booster,
    X: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    """Score transactions and return probabilities + binary predictions.

    Returns DataFrame with columns: row_id, prob, pred.
    """
    probs = model.predict(X) if isinstance(model, lgb.Booster) else model.predict_proba(X)[:, 1]

    return pd.DataFrame(
        {
            "row_id": X.index if X.index.name == "row_id" else range(len(X)),
            "prob": probs,
            "pred": (probs >= threshold).astype(np.int8),
        }
    )


def account_scores(
    txn_scores: pd.DataFrame,
    txn_meta: pd.DataFrame,
    inst_col: str = "from_inst",
    acct_col: str = "from_acct",
) -> pd.DataFrame:
    """Aggregate transaction scores to account level: max probability.

    Parameters
    ----------
    txn_scores : DataFrame
        Must have row_id, prob, pred columns.
    txn_meta : DataFrame
        Must have row_id and the inst/acct columns for joining.

    Returns
    -------
    DataFrame with (inst, acct) index and columns: max_prob, flagged.
    """
    merged = txn_scores.merge(
        txn_meta[["row_id", inst_col, acct_col]],
        on="row_id",
        how="left",
    )
    agg = (
        merged.groupby([inst_col, acct_col], observed=True)
        .agg(max_prob=("prob", "max"), flagged=("pred", "max"))
        .reset_index()
    )
    agg = agg.rename(columns={inst_col: "inst", acct_col: "acct"})
    return agg.set_index(["inst", "acct"])


def cross_bank_max_score(
    scores_by_inst: dict[int, pd.DataFrame],
    cross_txns: pd.DataFrame,
) -> pd.DataFrame:
    """For C1 siloed baseline: a cross-bank txn takes the max of its two banks' scores.

    Parameters
    ----------
    scores_by_inst : dict
        Mapping of institution_id -> per-institution transaction scores (row_id, prob, pred).
    cross_txns : DataFrame
        Cross-bank transactions with row_id, from_inst, to_inst.

    Returns
    -------
    DataFrame with row_id, prob, pred for cross-bank transactions.
    """
    # Pre-index scores by row_id for O(1) lookup
    indexed_scores = {}
    for inst, df in scores_by_inst.items():
        if "row_id" in df.columns:
            # check if row_id is already the index
            indexed_scores[inst] = df.set_index("row_id")
        else:
            indexed_scores[inst] = df

    rows = []
    for _, txn in cross_txns.iterrows():
        rid = txn["row_id"]
        from_inst = txn["from_inst"]
        to_inst = txn["to_inst"]

        prob_from = 0.0
        prob_to = 0.0

        if from_inst in indexed_scores:
            s = indexed_scores[from_inst]
            if rid in s.index:
                prob_from = float(s.loc[rid, "prob"])

        if to_inst in indexed_scores:
            s = indexed_scores[to_inst]
            if rid in s.index:
                prob_to = float(s.loc[rid, "prob"])

        rows.append({"row_id": rid, "prob": max(prob_from, prob_to)})

    result = pd.DataFrame(rows)
    if not result.empty:
        result["pred"] = (result["prob"] >= 0.5).astype(np.int8)
    return result


def time_inference(
    model: lgb.LGBMClassifier | lgb.Booster,
    X: pd.DataFrame,
    n_repeats: int = 10,
) -> dict[str, float]:
    """Time inference for benchmarking (laptop vs LinuxONE).

    Returns timing statistics in seconds.
    """
    times = []
    for _ in range(n_repeats):
        start = time.perf_counter()
        if isinstance(model, lgb.Booster):
            model.predict(X)
        else:
            model.predict_proba(X)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "n_samples": len(X),
        "n_repeats": n_repeats,
        "mean_sec": float(np.mean(times)),
        "std_sec": float(np.std(times)),
        "per_sample_ms": float(np.mean(times) / len(X) * 1000) if len(X) > 0 else 0.0,
    }
