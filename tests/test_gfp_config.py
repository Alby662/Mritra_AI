"""configs/gfp.yaml must actually configure snapml's GraphFeaturePreprocessor.

Guards against the exact bug found and fixed 2026-10-02 (Docs/DECISIONS.md): config keys
that don't match snapml's real schema, applied via setattr(), silently doing nothing.
"""

from __future__ import annotations

import copy

import pytest

from mritra.features.graph_gfp import load_gfp_config, valid_gfp_param_keys


def test_gfp_yaml_keys_are_all_valid_snapml_params() -> None:
    cfg = load_gfp_config()
    valid = valid_gfp_param_keys()
    unknown = set(cfg["params"]) - valid
    assert not unknown, f"configs/gfp.yaml has unknown param(s): {unknown}"


def test_every_gfp_yaml_key_actually_changes_get_params() -> None:
    snapml = pytest.importorskip("snapml")
    GraphFeaturePreprocessor = snapml.GraphFeaturePreprocessor

    cfg = load_gfp_config()
    gfp = GraphFeaturePreprocessor()
    gfp.set_params(dict(cfg["params"]))
    after = copy.deepcopy(gfp.get_params())

    for key, expected in cfg["params"].items():
        assert after[key] == expected, (
            f"configs/gfp.yaml sets {key}={expected} but get_params()[{key}] == "
            f"{after[key]} after applying it -- the config is not taking effect"
        )


def test_load_gfp_config_raises_on_unknown_key(tmp_path) -> None:
    bad = tmp_path / "bad_gfp.yaml"
    bad.write_text("params:\n  fan_in: true\n", encoding="utf-8")  # old, wrong key name
    with pytest.raises(ValueError, match="unknown"):
        load_gfp_config(bad)


def test_load_gfp_config_accepts_known_keys(tmp_path) -> None:
    ok = tmp_path / "ok_gfp.yaml"
    ok.write_text("params:\n  fan: true\n  degree: false\n", encoding="utf-8")
    cfg = load_gfp_config(ok)
    assert cfg["params"] == {"fan": True, "degree": False}
