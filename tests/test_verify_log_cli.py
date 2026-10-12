"""CLI compatibility tests for scripts/verify_log.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mritra.protocol.tlog import TransparencyLog
from scripts import verify_log


@pytest.fixture
def tlog_path(tmp_path: Path) -> Path:
    path = tmp_path / "tlog.db"
    tlog = TransparencyLog(path)
    tlog.append(
        type="boundary_exchange",
        actor="bank_0",
        code_sha256="c" * 64,
        input_sha256="a" * 64,
        output_sha256="b" * 64,
    )
    tlog.close()
    return path


def test_verify_log_accepts_positional_db_path(monkeypatch: pytest.MonkeyPatch, tlog_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", ["verify_log.py", str(tlog_path)])
    with pytest.raises(SystemExit) as excinfo:
        verify_log.main()
    assert excinfo.value.code == 0


def test_verify_log_accepts_db_flag(monkeypatch: pytest.MonkeyPatch, tlog_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", ["verify_log.py", "--db", str(tlog_path)])
    with pytest.raises(SystemExit) as excinfo:
        verify_log.main()
    assert excinfo.value.code == 0
