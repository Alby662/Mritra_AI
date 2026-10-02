"""Round-window consistency (CLAUDE.md rule 4, PROTOCOL.md §10).

Every configuration (C1, C3, C4) and every feature-computation path must use the same
round_window_sec, sourced from one place (configs/experiment.yaml: protocol.round_window_sec)
-- never its own hardcoded copy of the number.
"""

from __future__ import annotations

import numpy as np

from mritra.config import load_config
from mritra.protocol.rounds import round_id_for_ts
from mritra.protocol.rounds import round_window_sec as rounds_round_window_sec


def test_round_id_for_ts_matches_protocol_formula() -> None:
    # PROTOCOL.md §10: round_id = floor((ts - t0) / round_window_sec)
    assert round_id_for_ts(3_600, t0=0, window_sec=3_600) == 1
    assert round_id_for_ts(3_599, t0=0, window_sec=3_600) == 0
    assert round_id_for_ts(1_000 + 3_600 * 5 + 10, t0=1_000, window_sec=3_600) == 5
    arr = np.array([0, 3_599, 3_600, 7_199, 7_200])
    np.testing.assert_array_equal(
        round_id_for_ts(arr, t0=0, window_sec=3_600), np.array([0, 0, 1, 1, 2])
    )


def test_rounds_module_reads_config_round_window_sec() -> None:
    assert rounds_round_window_sec() == load_config()["protocol"]["round_window_sec"]


def test_graph_gfp_default_window_matches_shared_source() -> None:
    import pandas as pd
    import pytest

    from mritra.features.graph_gfp import compute_gfp_features, load_gfp_config

    pytest.importorskip("snapml")
    df = pd.DataFrame(
        {
            "row_id": [0, 1, 2],
            "from_bank": [0, 0, 0],
            "from_acct": ["A", "B", "A"],
            "to_bank": [1, 1, 1],
            "to_acct": ["B", "A", "B"],
            "ts": [1_000, 2_000, 3_000],
            "amt_paid": [10.0, 20.0, 30.0],
        }
    )
    cfg = load_gfp_config()
    explicit = compute_gfp_features(
        df.copy(), t0=0, gfp_cfg=cfg, round_window_sec=rounds_round_window_sec()
    )
    default = compute_gfp_features(df.copy(), t0=0, gfp_cfg=cfg)  # round_window_sec=None
    pd.testing.assert_frame_equal(explicit.sort_index(), default.sort_index())


def test_replay_stream_has_no_hardcoded_window_constant() -> None:
    import scripts.replay_stream as replay_stream

    # A module-level HOUR_SEC (or similar) hardcoded constant would silently diverge from
    # configs/experiment.yaml if the config value ever changes; it must not exist.
    assert not hasattr(replay_stream, "HOUR_SEC")
    assert replay_stream.get_round_window_sec() == load_config()["protocol"]["round_window_sec"]
