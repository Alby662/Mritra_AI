
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

# Stable, verified names for compute_behavioural_features' output columns (own source,
# not a third-party library) -- in the order they are added to `feats` below.
FEATURE_COLUMNS = [
    "sender_velocity_1h",
    "sender_velocity_24h",
    "sender_velocity_7d",
    "pass_through_ratio",
    "cross_inst_share",
    "format_diversity",
    "currency_diversity",
    "baseline_deviation",
]


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

    logger.info("Computing behavioural features for %d transactions", n)

    # --- Pre-extract numpy arrays (avoids slow df.iloc[i] in loops) ---
    row_ids = df["row_id"].to_numpy()
    ts = df["ts"].to_numpy(dtype=np.int64)
    amt_paid = df["amt_paid"].to_numpy(dtype=np.float64)
    amt_recv_arr = df["amt_recv"].to_numpy(dtype=np.float64)
    from_inst = df["from_inst"].to_numpy()
    to_inst = df["to_inst"].to_numpy()
    fmts = df["fmt"].astype(str).to_numpy()
    curs = df["cur_paid"].astype(str).to_numpy()

    sender_key = (df["from_inst"].astype(str) + "_" + df["from_acct"].astype(str)).to_numpy()
    receiver_key = (df["to_inst"].astype(str) + "_" + df["to_acct"].astype(str)).to_numpy()

    feats: dict[str, np.ndarray] = {"row_id": row_ids}

    # --- Build sender group indices once (reused by velocity) ---
    _idx_df = pd.DataFrame({"sk": sender_key})
    sender_groups = {k: grp.index.to_numpy() for k, grp in _idx_df.groupby("sk")}

    # --- 1. Velocity: searchsorted per group, O(n log n) total ---
    for window_name, window_sec in WINDOWS.items():
        velocity = np.zeros(n, dtype=np.float64)
        for indices in sender_groups.values():
            group_ts = ts[indices]  # sorted since df is sorted by ts
            left = np.searchsorted(group_ts, group_ts - window_sec, side="left")
            velocity[indices] = np.arange(len(indices)) - left
        feats[f"sender_velocity_{window_name}"] = velocity
        logger.info("  velocity %s done", window_name)

    # --- 2. Pass-through ratio: numpy loop, O(n) ---
    acct_sent: dict[str, float] = {}
    acct_recv: dict[str, float] = {}
    cum_sent = np.zeros(n, dtype=np.float64)
    cum_recv = np.zeros(n, dtype=np.float64)

    for i in range(n):
        sk = sender_key[i]
        rk = receiver_key[i]
        acct_sent[sk] = acct_sent.get(sk, 0.0) + amt_paid[i]
        acct_recv[rk] = acct_recv.get(rk, 0.0) + amt_recv_arr[i]
        cum_sent[i] = acct_sent[sk]
        cum_recv[i] = acct_recv.get(sk, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        feats["pass_through_ratio"] = np.where(cum_recv > 0, cum_sent / cum_recv, 0.0)
    logger.info("  pass_through_ratio done")

    # --- 3. Cross-institution share: vectorized groupby + cumsum ---
    is_cross = (from_inst != to_inst).astype(np.float64)
    _cross_df = pd.DataFrame({"sk": sender_key, "cross": is_cross, "one": np.ones(n)})
    cum_cross = _cross_df.groupby("sk")["cross"].cumsum().to_numpy()
    cum_total = _cross_df.groupby("sk")["one"].cumsum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        feats["cross_inst_share"] = np.where(cum_total > 0, cum_cross / cum_total, 0.0)
    logger.info("  cross_inst_share done")

    # --- 4. Format diversity: vectorized with duplicated + cumsum ---
    _fmt_df = pd.DataFrame({"sk": sender_key, "fmt": fmts})
    first_fmt = (~_fmt_df.duplicated(subset=["sk", "fmt"], keep="first")).astype(np.float64)
    _fmt_df["first"] = first_fmt
    feats["format_diversity"] = _fmt_df.groupby("sk")["first"].cumsum().to_numpy()
    logger.info("  format_diversity done")

    # --- 5. Currency diversity: vectorized with duplicated + cumsum ---
    _cur_df = pd.DataFrame({"sk": sender_key, "cur": curs})
    first_cur = (~_cur_df.duplicated(subset=["sk", "cur"], keep="first")).astype(np.float64)
    _cur_df["first"] = first_cur
    feats["currency_diversity"] = _cur_df.groupby("sk")["first"].cumsum().to_numpy()
    logger.info("  currency_diversity done")

    # --- 6. Baseline deviation: Vectorized with pandas rolling ---
    _df = pd.DataFrame(
        {
            "sk": sender_key,
            "ts": pd.to_datetime(ts, unit="s"),
            "amt": amt_paid,
            "amt_sq": amt_paid**2,
        }
    )
    # Data is already sorted by ts, so df is ordered
    roll = _df.groupby("sk").rolling("30D", on="ts")

    r_sum = roll["amt"].sum().reset_index(level=0, drop=True).sort_index().values
    r_sum_sq = roll["amt_sq"].sum().reset_index(level=0, drop=True).sort_index().values
    r_count = roll["amt"].count().reset_index(level=0, drop=True).sort_index().values

    # Exclude current row to prevent leakage
    count_excl = r_count - 1
    sum_excl = r_sum - amt_paid
    sum_sq_excl = r_sum_sq - amt_paid**2

    baseline_dev = np.zeros(n, dtype=np.float64)
    mask = count_excl >= 2

    mu = sum_excl[mask] / count_excl[mask]
    var = (sum_sq_excl[mask] / count_excl[mask]) - mu**2
    sigma = np.sqrt(np.maximum(var, 0))

    valid = sigma > 1e-9
    baseline_dev[mask] = np.where(valid, (amt_paid[mask] - mu) / np.where(valid, sigma, 1.0), 0.0)

    feats["baseline_deviation"] = baseline_dev
    logger.info("  baseline_deviation done")

    result = pd.DataFrame(feats)
    return result.set_index("row_id")
