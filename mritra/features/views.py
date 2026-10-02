"""Single source of truth for what each configuration can see (PREREGISTRATION §5).

    C1 Siloed   : institution b's own edges (its internal transactions + its own side of
                  cross-bank transactions), its own accounts only.
    C2 Federated: not implemented for this datathon build (raises NotImplementedError).
    C3 Mritra   : C1's edge scope, plus enclave network features for institution b's own
                  accounts (mritra.features.network.compute_network_features).
    C4 Oracle   : every edge, every account -- no institution restriction.

This module does not compute features itself (that stays in behaviour.py / graph_gfp.py /
network.py); it decides WHICH rows and WHICH columns a configuration is allowed to see, so
that scripts/build_features.py (and anything else) has exactly one place that encodes the
C1-C4 visibility rules, rather than re-deriving them per call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

Config = Literal["C1", "C2", "C3", "C4"]
CONFIGS: tuple[Config, ...] = ("C1", "C2", "C3", "C4")

# Columns that are derived from is_laund (mritra/data/roles.py) or are the label itself.
# A feature_columns list containing any of these is a leakage bug, not a valid feature set
# -- CLAUDE.md rule: "labels... never a feature."
_LABEL_DERIVED_COLUMNS = frozenset(
    {"is_laund", "role", "sends_laund", "recvs_laund", "amt_in_laund", "amt_in_total"}
)


@dataclass(frozen=True)
class FeatureView:
    """What one configuration can see: which edges, which accounts, which columns."""

    config: Config
    bank_id: int | None  # None for C4 (not institution-scoped)
    edges: pd.DataFrame
    own_accounts: frozenset[str] | None  # None for C4 ("all accounts")
    feature_columns: list[str]


def account_key(inst: int, acct: str) -> str:
    """The ``{inst}_{acct}`` key convention used throughout the protocol layer
    (mritra/services/*, mritra/features/network.py)."""
    return f"{inst}_{acct}"


def _own_accounts(df: pd.DataFrame, bank_id: int) -> frozenset[str]:
    senders = df.loc[df["from_inst"] == bank_id, "from_acct"]
    receivers = df.loc[df["to_inst"] == bank_id, "to_acct"]
    return frozenset(account_key(bank_id, a) for a in pd.concat([senders, receivers]).unique())


def _assert_no_label_derived_columns(feature_columns: list[str]) -> None:
    leaked = _LABEL_DERIVED_COLUMNS.intersection(feature_columns)
    if leaked:
        raise ValueError(
            f"feature_columns contains label-derived column(s) {sorted(leaked)} -- "
            "these come from is_laund (mritra/data/roles.py) and must never be a feature"
        )


def feature_view(
    config: Config,
    df: pd.DataFrame,
    bank_id: int | None = None,
    *,
    behaviour_columns: list[str] | None = None,
    gfp_n_feat: int | None = None,
    network_summary_dim: int | None = None,
) -> FeatureView:
    """Build the edge set and feature column list visible to ``config``.

    Parameters
    ----------
    df : DataFrame
        Must already carry ``from_inst``/``to_inst`` (``mritra.data.partition.add_institutions``).
    bank_id : int, optional
        Institution index. Required for C1 and C3; ignored for C4.
    behaviour_columns : list[str], optional
        Defaults to ``mritra.features.behaviour.FEATURE_COLUMNS``.
    gfp_n_feat : int, optional
        Number of GFP columns to name (``mritra.features.graph_gfp.gfp_feature_names``);
        omitted (no GFP columns) if ``None``.
    network_summary_dim : int, optional
        Boundary-summary vector width, for C3's network feature names
        (``mritra.features.network.network_feature_names``); required for C3.
    """
    from mritra.features.behaviour import FEATURE_COLUMNS as DEFAULT_BEHAVIOUR_COLUMNS
    from mritra.features.graph_gfp import gfp_feature_names
    from mritra.features.network import network_feature_names

    if config not in CONFIGS:
        raise ValueError(f"unknown config {config!r}; expected one of {CONFIGS}")
    if config == "C2":
        raise NotImplementedError("C2 (federated) is not implemented for this datathon build")

    behaviour_cols = (
        behaviour_columns if behaviour_columns is not None else list(DEFAULT_BEHAVIOUR_COLUMNS)
    )
    gfp_cols = gfp_feature_names(gfp_n_feat) if gfp_n_feat is not None else []

    if config in ("C1", "C3"):
        if bank_id is None:
            raise ValueError(f"{config} requires bank_id")
        edges = df[(df["from_inst"] == bank_id) | (df["to_inst"] == bank_id)]
        own_accounts = _own_accounts(df, bank_id)
        feature_columns = [*gfp_cols, *behaviour_cols]
        if config == "C3":
            if network_summary_dim is None:
                raise ValueError("C3 requires network_summary_dim")
            feature_columns = feature_columns + network_feature_names(network_summary_dim)
        _assert_no_label_derived_columns(feature_columns)
        return FeatureView(config, bank_id, edges, own_accounts, feature_columns)

    # C4: everything, no institution restriction.
    feature_columns = [*gfp_cols, *behaviour_cols]
    _assert_no_label_derived_columns(feature_columns)
    return FeatureView("C4", None, df, None, feature_columns)
