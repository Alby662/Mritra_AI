"""Assign proxy role labels to accounts (PREREGISTRATION §4 / plan §6.2).

Definitions (from plan §6.2 / experiment.yaml):
  - source:              sends laundering, never receives it
  - mule:                both receives AND sends laundering
  - innocent_recipient:  receives laundering, sends none onward,
                         laundering < innocent_recipient_max_laundering_share of inflow
  - involved:            receives or sends laundering but doesn't meet the above criteria
  - clean:               no laundering involvement
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AccountRoles:
    """Per-account role labels and the underlying aggregates."""

    df: pd.DataFrame  # indexed by (inst, acct), columns below
    # sends_laund, recvs_laund, amt_in_total, amt_in_laund, role


def assign_roles(
    df: pd.DataFrame,
    max_innocent_share: float = 0.10,
) -> pd.DataFrame:
    """Compute per-account role from transaction-level data.

    Parameters
    ----------
    df : DataFrame
        Must contain: from_inst, from_acct, to_inst, to_acct, amt_recv, is_laund.
    max_innocent_share : float
        Laundering share threshold for the innocent-recipient role.

    Returns
    -------
    DataFrame indexed by (inst, acct) with columns:
        sends_laund, recvs_laund, amt_in_total, amt_in_laund, role
    """
    laund = df[df["is_laund"] == 1]

    # Accounts that *send* at least one laundering txn
    senders = set(zip(laund["from_inst"], laund["from_acct"], strict=True))

    # Accounts that *receive* at least one laundering txn
    receivers = set(zip(laund["to_inst"], laund["to_acct"], strict=True))

    # All accounts
    from_keys = df[["from_inst", "from_acct"]].rename(
        columns={"from_inst": "inst", "from_acct": "acct"}
    )
    to_keys = df[["to_inst", "to_acct"]].rename(
        columns={"to_inst": "inst", "to_acct": "acct"}
    )
    all_accounts = pd.concat([from_keys, to_keys]).drop_duplicates().reset_index(drop=True)

    # Inflow totals per receiver account
    inflow = (
        df.groupby(["to_inst", "to_acct"], observed=True)
        .agg(amt_in_total=("amt_recv", "sum"))
        .reset_index()
        .rename(columns={"to_inst": "inst", "to_acct": "acct"})
    )

    # Laundering inflow
    laund_inflow = (
        laund.groupby(["to_inst", "to_acct"], observed=True)
        .agg(amt_in_laund=("amt_recv", "sum"))
        .reset_index()
        .rename(columns={"to_inst": "inst", "to_acct": "acct"})
    )

    roles = all_accounts.merge(inflow, on=["inst", "acct"], how="left")
    roles = roles.merge(laund_inflow, on=["inst", "acct"], how="left")
    roles["amt_in_total"] = roles["amt_in_total"].fillna(0.0)
    roles["amt_in_laund"] = roles["amt_in_laund"].fillna(0.0)

    keys = list(zip(roles["inst"], roles["acct"], strict=True))
    roles["sends_laund"] = [k in senders for k in keys]
    roles["recvs_laund"] = [k in receivers for k in keys]

    # Assign roles
    def _role(row: pd.Series) -> str:
        s, r = row["sends_laund"], row["recvs_laund"]
        if not s and not r:
            return "clean"
        if s and r:
            return "mule"
        if s and not r:
            return "source"
        # r and not s → candidate innocent recipient
        share = row["amt_in_laund"] / row["amt_in_total"] if row["amt_in_total"] > 0 else 0.0
        if share < max_innocent_share:
            return "innocent_recipient"
        return "involved"

    roles["role"] = roles.apply(_role, axis=1)
    roles["role"] = roles["role"].astype("category")
    return roles.set_index(["inst", "acct"])
