"""Lead time before exit metric (plan §10).

Per pattern with an exit transaction: ``t_exit − t_first_flag``; median +
share flagged before exit.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_lead_time(
    patterns: pd.DataFrame,
    txn_scores: pd.DataFrame,
    exit_formats: list[str],
    threshold: float,
) -> dict[str, Any]:
    """Compute lead time before exit for each pattern.

    Parameters
    ----------
    patterns : DataFrame
        Parsed patterns with pattern_id, ts, fmt, row_id columns
        (from patterns.parquet joined with trans to get row_id).
    txn_scores : DataFrame
        Transaction scores with row_id, prob, pred columns.
    exit_formats : list[str]
        Payment format strings that count as exit (e.g. ["Cash", "Bitcoin"]).
    threshold : float
        Classification threshold.

    Returns
    -------
    dict with lead_time stats.
    """
    if not exit_formats:
        logger.warning("exit_formats is empty — cannot compute lead time")
        return {"note": "exit_formats not configured"}

    # Join pattern txns with scores
    scored = patterns.merge(txn_scores[["row_id", "prob"]], on="row_id", how="left")
    scored["flagged"] = scored["prob"] >= threshold

    results = []
    for pid, group in scored.groupby("pattern_id", observed=True):
        # Find exit transactions
        exits = group[group["fmt"].isin(exit_formats)]
        if exits.empty:
            continue

        t_exit = exits["ts"].min()

        # Find first flagged transaction in this pattern
        flagged = group[group["flagged"]]
        if flagged.empty:
            results.append({
                "pattern_id": pid,
                "t_exit": int(t_exit),
                "t_first_flag": None,
                "lead_time_sec": None,
                "flagged_before_exit": False,
            })
            continue

        t_first_flag = flagged["ts"].min()
        lead = int(t_exit - t_first_flag)

        results.append({
            "pattern_id": pid,
            "t_exit": int(t_exit),
            "t_first_flag": int(t_first_flag),
            "lead_time_sec": lead,
            "flagged_before_exit": t_first_flag < t_exit,
        })

    if not results:
        return {
            "n_patterns_with_exit": 0,
            "share_flagged_before_exit": 0.0,
            "median_lead_time_sec": None,
        }

    df = pd.DataFrame(results)
    lead_times = df[df["flagged_before_exit"]]["lead_time_sec"].dropna()

    return {
        "n_patterns_with_exit": len(df),
        "n_flagged_before_exit": int(df["flagged_before_exit"].sum()),
        "share_flagged_before_exit": float(df["flagged_before_exit"].mean()),
        "median_lead_time_sec": float(lead_times.median()) if len(lead_times) > 0 else None,
        "mean_lead_time_sec": float(lead_times.mean()) if len(lead_times) > 0 else None,
        "lead_time_details": results,
    }
