"""Round/window arithmetic shared by every feature-computation path (PROTOCOL.md §10).

``round_id = floor((ts - t0) / round_window_sec)``

Every configuration (C1, C3, C4) and every institution's view must use the same
``round_window_sec`` *and* the same ``t0`` so that round *N* means the identical
wall-clock window everywhere — not a window relative to whatever subset of data a
particular call happens to see. ``t0`` is the first train timestamp for offline runs, the
first test-period timestamp for the live demo (PROTOCOL.md §10).
"""

from __future__ import annotations

import numpy as np


def round_window_sec() -> int:
    """The single ``round_window_sec`` every feature path must use (configs/experiment.yaml)."""
    from mritra.config import load_config

    return int(load_config()["protocol"]["round_window_sec"])


def round_id_for_ts(
    ts: np.ndarray | int, t0: int, window_sec: int | None = None
) -> np.ndarray | int:
    """Round index for timestamp(s) ``ts``, per PROTOCOL.md §10's formula."""
    if window_sec is None:
        window_sec = round_window_sec()
    return (ts - t0) // window_sec
