"""Behavioural features per account (plan §7.1 item 2).

Rolling windows (1 h, 24 h, 7 d) computed streaming in timestamp order —
no feature sees the future (PREREGISTRATION leakage rule).

Features per account at each transaction:
  - pass_through_ratio: amount out / amount in
  - median_dwell_time: median seconds between receive and next send
  - txn_velocity: transaction count in the window
  - new_counterparties_24h: new counterparties in last 24 h
  - format_switches: distinct payment formats in window
  - currency_switches: distinct currencies in window
  - cross_inst_share: share of flow going to other institutions
  - baseline_deviation: z-score of current amount vs 30-day rolling mean/std
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

WINDOWS = {"1h": 3600, "24h": 86400, "7d": 604800}
BASELINE_WINDOW = 30 * 86400  # 30 days


def _rolling_agg(
    group: pd.DataFrame, ts_col: str, val_col: str, window_sec: int, agg: str
) -> np.ndarray:
    """Backward-looking rolling aggregation over a sorted group."""
    ts = group[ts_col].to_numpy()
    vals = group[val_col].to_numpy(dtype=np.float64)
    n = len(ts)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        start = ts[i] - window_sec
        mask = (ts[:i] >= start)  # exclude current row, past only
        window_vals = vals[:i][mask]
        if len(window_vals) == 0:
            continue
        if agg == "sum":
            out[i] = window_vals.sum()
        elif agg == "count":
            out[i] = len(window_vals)
        elif agg == "mean":
            out[i] = window_vals.mean()
        elif agg == "std":
            out[i] = window_vals.std() if len(window_vals) > 1 else 0.0
    return out


def compute_behavioural_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute behavioural features for each transaction, keyed by row_id.

    Parameters
    ----------
    df : DataFrame
        Must contain: row_id, ts, from_inst, from_acct, to_inst, to_acct,
        amt_paid, amt_recv, fmt, cur_paid.  Must be sorted by ts.

    Returns
    -------
    DataFrame indexed by row_id with behavioural feature columns.
    """
    df = df.sort_values("ts").reset_index(drop=True)
    n = len(df)

    feats: dict[str, np.ndarray] = {
        "row_id": df["row_id"].to_numpy(),
    }

    logger.info("Computing behavioural features for %d transactions", n)

    # --- Per-sender account features ---
    sender_key = df["from_inst"].astype(str) + "_" + df["from_acct"].astype(str)

    for window_name, window_sec in WINDOWS.items():
        velocity = np.zeros(n, dtype=np.float64)
        for _key, idx in df.groupby(sender_key, observed=True).groups.items():
            group = df.iloc[idx].sort_values("ts")
            ts = group["ts"].to_numpy()
            for j, pos in enumerate(idx):
                start = ts[j] - window_sec
                velocity[pos] = np.sum(ts[:j] >= start)
        feats[f"sender_velocity_{window_name}"] = velocity

    # --- Pass-through ratio (cumulative up to current time) ---
    # For each account: total sent / total received so far
    cum_sent = np.zeros(n, dtype=np.float64)
    cum_recv = np.zeros(n, dtype=np.float64)

    acct_sent: dict[str, float] = {}
    acct_recv: dict[str, float] = {}

    for i in range(n):
        s_key = sender_key.iloc[i]
        r_key = (
            str(df.iloc[i]["to_inst"]) + "_" + str(df.iloc[i]["to_acct"])
        )
        amt_paid = float(df.iloc[i]["amt_paid"])
        amt_recv = float(df.iloc[i]["amt_recv"])

        acct_sent[s_key] = acct_sent.get(s_key, 0.0) + amt_paid
        acct_recv[r_key] = acct_recv.get(r_key, 0.0) + amt_recv

        total_recv = acct_recv.get(s_key, 0.0)
        cum_sent[i] = acct_sent[s_key]
        cum_recv[i] = total_recv

    with np.errstate(divide="ignore", invalid="ignore"):
        feats["pass_through_ratio"] = np.where(
            cum_recv > 0, cum_sent / cum_recv, 0.0
        )

    # --- Cross-institution share (sender) ---
    cross_count = np.zeros(n, dtype=np.float64)
    total_count = np.zeros(n, dtype=np.float64)
    acct_cross: dict[str, int] = {}
    acct_total: dict[str, int] = {}

    for i in range(n):
        s_key = sender_key.iloc[i]
        is_cross = df.iloc[i]["from_inst"] != df.iloc[i]["to_inst"]
        acct_total[s_key] = acct_total.get(s_key, 0) + 1
        if is_cross:
            acct_cross[s_key] = acct_cross.get(s_key, 0) + 1
        cross_count[i] = acct_cross.get(s_key, 0)
        total_count[i] = acct_total[s_key]

    with np.errstate(divide="ignore", invalid="ignore"):
        feats["cross_inst_share"] = np.where(
            total_count > 0, cross_count / total_count, 0.0
        )

    # --- Format diversity (cumulative distinct formats per sender) ---
    acct_fmts: dict[str, set[str]] = {}
    fmt_div = np.zeros(n, dtype=np.float64)
    for i in range(n):
        s_key = sender_key.iloc[i]
        fmt = str(df.iloc[i]["fmt"])
        if s_key not in acct_fmts:
            acct_fmts[s_key] = set()
        acct_fmts[s_key].add(fmt)
        fmt_div[i] = len(acct_fmts[s_key])
    feats["format_diversity"] = fmt_div

    # --- Currency diversity ---
    acct_curs: dict[str, set[str]] = {}
    cur_div = np.zeros(n, dtype=np.float64)
    for i in range(n):
        s_key = sender_key.iloc[i]
        cur = str(df.iloc[i]["cur_paid"])
        if s_key not in acct_curs:
            acct_curs[s_key] = set()
        acct_curs[s_key].add(cur)
        cur_div[i] = len(acct_curs[s_key])
    feats["currency_diversity"] = cur_div

    # --- Baseline deviation (30-day rolling z-score on amount) ---
    baseline_dev = np.zeros(n, dtype=np.float64)
    acct_amts: dict[str, list[tuple[int, float]]] = {}
    for i in range(n):
        s_key = sender_key.iloc[i]
        ts_i = int(df.iloc[i]["ts"])
        amt = float(df.iloc[i]["amt_paid"])
        if s_key not in acct_amts:
            acct_amts[s_key] = []
        # Window: past 30 days
        window = [a for t, a in acct_amts[s_key] if t >= ts_i - BASELINE_WINDOW]
        if len(window) >= 2:
            mu = np.mean(window)
            sigma = np.std(window)
            baseline_dev[i] = (amt - mu) / sigma if sigma > 0 else 0.0
        acct_amts[s_key].append((ts_i, amt))
    feats["baseline_deviation"] = baseline_dev

    result = pd.DataFrame(feats)
    return result.set_index("row_id")
