"""scripts/config_audit.py: C1-C4 only differ in feature columns and edge scope."""

from __future__ import annotations

from scripts.config_audit import build_config_audit


def test_configs_identical_except_feature_columns_and_edge_scope() -> None:
    audit = build_config_audit()
    configs = audit["configs"]

    varying_keys = {"feature_columns", "edge_scope"}
    shared_keys = set(configs["C1"]) - varying_keys

    for key in shared_keys:
        c1, c3, c4 = configs["C1"][key], configs["C3"][key], configs["C4"][key]
        assert c1 == c3 == c4, f"{key} differs between C1/C3/C4: {c1!r} / {c3!r} / {c4!r}"

    # The varying keys must actually vary in the ways PREREGISTRATION §5 specifies.
    assert configs["C1"]["edge_scope"] != configs["C4"]["edge_scope"]
    assert (
        configs["C3"]["feature_columns"][: len(configs["C1"]["feature_columns"])]
        == (configs["C1"]["feature_columns"])
    )
    assert len(configs["C3"]["feature_columns"]) > len(configs["C1"]["feature_columns"])
    # C1 and C4 see the same kind of features (GFP + behavioural), just on different edge
    # scopes -- so their feature_columns lists match even though edge_scope differs.
    assert configs["C1"]["feature_columns"] == configs["C4"]["feature_columns"]


def test_config_audit_has_measured_not_guessed_gfp_count() -> None:
    audit = build_config_audit()
    n = audit["gfp_n_feat_measured_on_toy_data"]
    assert n > 0
    assert len(audit["configs"]["C1"]["feature_columns"]) >= n
