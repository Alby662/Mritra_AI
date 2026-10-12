"""Tests for the transparency log (plan §9.5).

Asserts: any edited log row breaks verification.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from mritra.protocol.tlog import GENESIS_HASH, TransparencyLog, verify_chain


@pytest.fixture
def tlog_path(tmp_path: Path) -> Path:
    return tmp_path / "test_tlog.db"


class TestTransparencyLog:
    """Transparency log append and chain verification."""

    def test_empty_chain_is_valid(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        entries = tlog.entries()
        assert len(entries) == 0
        valid, broken = verify_chain(entries)
        assert valid is True
        assert broken is None
        tlog.close()

    def test_single_entry_chain(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        entry = tlog.append(
            type="boundary_exchange",
            actor="bank_0",
            code_sha256="c" * 64,
            input_sha256="a" * 64,
            output_sha256="b" * 64,
        )
        assert entry.prev_hash == GENESIS_HASH
        entries = tlog.entries()
        valid, broken = verify_chain(entries)
        assert valid is True
        assert broken is None
        tlog.close()

    def test_multi_entry_chain(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(5):
            tlog.append(
                type="boundary_exchange",
                actor=f"bank_{i}",
                code_sha256="c" * 64,
                input_sha256=f"{i:064x}",
                output_sha256=f"{i + 100:064x}",
            )
        entries = tlog.entries()
        assert len(entries) == 5
        valid, broken = verify_chain(entries)
        assert valid is True
        tlog.close()

    def test_chain_links_correctly(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        e1 = tlog.append(
            type="q1",
            actor="bank_0",
            code_sha256="c" * 64,
            input_sha256="a" * 64,
            output_sha256="b" * 64,
        )
        e2 = tlog.append(
            type="q2",
            actor="bank_1",
            code_sha256="c" * 64,
            input_sha256="d" * 64,
            output_sha256="e" * 64,
        )
        assert e2.prev_hash == e1.entry_hash
        tlog.close()


class TestTamperDetection:
    """Any edit to a log row breaks the chain."""

    def test_tampered_entry_hash_detected(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(3):
            tlog.append(
                type="q",
                actor=f"bank_{i}",
                code_sha256="c" * 64,
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
            )
        entries = tlog.entries()
        # Tamper with the middle entry's hash
        entries[1] = dataclasses.replace(
            entries[1],
            entry_hash="tampered" + "0" * 56,
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[1].seq
        tlog.close()

    def test_tampered_prev_hash_detected(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(3):
            tlog.append(
                type="q",
                actor=f"bank_{i}",
                code_sha256="c" * 64,
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
            )
        entries = tlog.entries()
        # Tamper with the last entry's prev_hash
        entries[2] = dataclasses.replace(
            entries[2],
            prev_hash="tampered" + "0" * 56,
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[2].seq
        tlog.close()

    def test_tampered_content_detected(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(3):
            tlog.append(
                type="q",
                actor=f"bank_{i}",
                code_sha256="c" * 64,
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
            )
        entries = tlog.entries()
        # Tamper with content but keep hash — chain should break
        entries[1] = dataclasses.replace(
            entries[1],
            actor="EVIL_BANK",  # tampered
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[1].seq
        tlog.close()
