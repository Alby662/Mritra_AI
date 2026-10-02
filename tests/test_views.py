"""mritra/features/views.py: single source of truth for C1-C4 visibility."""

from __future__ import annotations

import pandas as pd
import pytest

from mritra.data.partition import add_institutions
from mritra.features.behaviour import FEATURE_COLUMNS as BEHAVIOUR_FEATURE_COLUMNS
from mritra.features.views import account_key, feature_view


def _toy_df() -> pd.DataFrame:
    # 4 institutions: 0 and 1 trade with each other and internally; 2 and 3 likewise.
    inst_of = {10: 0, 11: 0, 20: 1, 21: 1, 30: 2, 31: 3}
    rows = [
        {"from_bank": 10, "from_acct": "a", "to_bank": 11, "to_acct": "b"},  # inst0 internal
        {"from_bank": 10, "from_acct": "a", "to_bank": 20, "to_acct": "c"},  # inst0 <-> inst1
        {"from_bank": 20, "from_acct": "c", "to_bank": 21, "to_acct": "d"},  # inst1 internal
        {"from_bank": 30, "from_acct": "e", "to_bank": 31, "to_acct": "f"},  # inst2 <-> inst3
    ]
    df = pd.DataFrame(rows)
    return add_institutions(df, inst_of)


def test_c1_view_has_no_account_ids_owned_by_another_bank() -> None:
    df = _toy_df()
    view0 = feature_view("C1", df, bank_id=0)
    view1 = feature_view("C1", df, bank_id=1)

    # Bank 0's own_accounts must only ever be keyed "0_...", never "1_...".
    assert all(key.startswith("0_") for key in view0.own_accounts)
    assert all(key.startswith("1_") for key in view1.own_accounts)
    # And the two banks' own-account sets must be disjoint.
    assert view0.own_accounts.isdisjoint(view1.own_accounts)


def test_c1_view_edges_are_only_those_touching_the_bank() -> None:
    df = _toy_df()
    view0 = feature_view("C1", df, bank_id=0)
    # inst0 touches rows 0 (internal) and 1 (cross to inst1) -- not row 2 or row 3.
    assert set(view0.edges.index) == {0, 1}

    view3 = feature_view("C1", df, bank_id=3)
    assert set(view3.edges.index) == {3}


def test_c4_is_a_superset_of_every_c1_view() -> None:
    df = _toy_df()
    c4 = feature_view("C4", df)
    assert c4.own_accounts is None  # unrestricted
    assert len(c4.edges) == len(df)

    for bank_id in (0, 1, 2, 3):
        c1 = feature_view("C1", df, bank_id=bank_id)
        assert set(c1.edges.index).issubset(set(c4.edges.index))


def test_c3_view_is_c1_view_plus_network_feature_columns() -> None:
    df = _toy_df()
    c1 = feature_view("C1", df, bank_id=0, gfp_n_feat=3)
    c3 = feature_view("C3", df, bank_id=0, gfp_n_feat=3, network_summary_dim=2)

    assert set(c3.edges.index) == set(c1.edges.index)
    assert c3.own_accounts == c1.own_accounts
    assert c3.feature_columns[: len(c1.feature_columns)] == c1.feature_columns
    # Network columns are appended, not interleaved: fixed 5 + 3 * summary_dim.
    assert len(c3.feature_columns) == len(c1.feature_columns) + 5 + 3 * 2


def test_c2_raises_not_implemented() -> None:
    df = _toy_df()
    with pytest.raises(NotImplementedError):
        feature_view("C2", df, bank_id=0)


def test_c3_requires_network_summary_dim() -> None:
    df = _toy_df()
    with pytest.raises(ValueError, match="network_summary_dim"):
        feature_view("C3", df, bank_id=0)


def test_c1_and_c3_require_bank_id() -> None:
    df = _toy_df()
    with pytest.raises(ValueError, match="bank_id"):
        feature_view("C1", df)
    with pytest.raises(ValueError, match="bank_id"):
        feature_view("C3", df, network_summary_dim=2)


def test_label_derived_column_fails_hard() -> None:
    df = _toy_df()
    with pytest.raises(ValueError, match="label-derived"):
        feature_view("C1", df, bank_id=0, behaviour_columns=["role", "pass_through_ratio"])
    with pytest.raises(ValueError, match="label-derived"):
        feature_view("C4", df, behaviour_columns=["is_laund"])


def test_account_key_matches_protocol_convention() -> None:
    assert account_key(0, "a1") == "0_a1"


def test_behaviour_feature_columns_match_actual_output() -> None:
    # Guards against FEATURE_COLUMNS drifting out of sync with compute_behavioural_features.
    from mritra.features.behaviour import compute_behavioural_features

    df = pd.DataFrame(
        {
            "row_id": [0, 1],
            "ts": [1_000, 1_100],
            "from_inst": [0, 1],
            "from_acct": ["a", "b"],
            "to_inst": [1, 0],
            "to_acct": ["b", "a"],
            "amt_paid": [10.0, 20.0],
            "amt_recv": [9.0, 19.0],
            "fmt": ["ACH", "Wire"],
            "cur_paid": ["USD", "USD"],
        }
    )
    out = compute_behavioural_features(df)
    assert list(out.columns) == BEHAVIOUR_FEATURE_COLUMNS
