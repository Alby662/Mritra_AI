"""Tests for the transparency log (plan §9.5).

Asserts: any edited log row breaks verification.
"""

from __future__ import annotations

import tempfile
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
            requester="bank_0",
            query_type="boundary_exchange",
            input_sha256="a" * 64,
            output_sha256="b" * 64,
            enclave_code_sha256="c" * 64,
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
                requester=f"bank_{i}",
                query_type="boundary_exchange",
                input_sha256=f"{i:064x}",
                output_sha256=f"{i + 100:064x}",
                enclave_code_sha256="c" * 64,
            )
        entries = tlog.entries()
        assert len(entries) == 5
        valid, broken = verify_chain(entries)
        assert valid is True
        tlog.close()

    def test_chain_links_correctly(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        e1 = tlog.append(
            requester="bank_0",
            query_type="q1",
            input_sha256="a" * 64,
            output_sha256="b" * 64,
            enclave_code_sha256="c" * 64,
        )
        e2 = tlog.append(
            requester="bank_1",
            query_type="q2",
            input_sha256="d" * 64,
            output_sha256="e" * 64,
            enclave_code_sha256="c" * 64,
        )
        assert e2.prev_hash == e1.entry_hash
        tlog.close()


class TestTamperDetection:
    """Any edit to a log row breaks the chain."""

    def test_tampered_entry_hash_detected(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(3):
            tlog.append(
                requester=f"bank_{i}",
                query_type="q",
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
                enclave_code_sha256="c" * 64,
            )
        entries = tlog.entries()
        # Tamper with the middle entry's hash
        entries[1] = type(entries[1])(
            seq=entries[1].seq,
            ts=entries[1].ts,
            requester=entries[1].requester,
            query_type=entries[1].query_type,
            input_sha256=entries[1].input_sha256,
            output_sha256=entries[1].output_sha256,
            enclave_code_sha256=entries[1].enclave_code_sha256,
            prev_hash=entries[1].prev_hash,
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
                requester=f"bank_{i}",
                query_type="q",
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
                enclave_code_sha256="c" * 64,
            )
        entries = tlog.entries()
        # Tamper with the last entry's prev_hash
        entries[2] = type(entries[2])(
            seq=entries[2].seq,
            ts=entries[2].ts,
            requester=entries[2].requester,
            query_type=entries[2].query_type,
            input_sha256=entries[2].input_sha256,
            output_sha256=entries[2].output_sha256,
            enclave_code_sha256=entries[2].enclave_code_sha256,
            prev_hash="tampered" + "0" * 56,
            entry_hash=entries[2].entry_hash,
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[2].seq
        tlog.close()

    def test_tampered_content_detected(self, tlog_path):
        tlog = TransparencyLog(tlog_path)
        for i in range(3):
            tlog.append(
                requester=f"bank_{i}",
                query_type="q",
                input_sha256=f"{i:064x}",
                output_sha256=f"{i:064x}",
                enclave_code_sha256="c" * 64,
            )
        entries = tlog.entries()
        # Tamper with content but keep hash — chain should break
        entries[1] = type(entries[1])(
            seq=entries[1].seq,
            ts=entries[1].ts,
            requester="EVIL_BANK",  # tampered
            query_type=entries[1].query_type,
            input_sha256=entries[1].input_sha256,
            output_sha256=entries[1].output_sha256,
            enclave_code_sha256=entries[1].enclave_code_sha256,
            prev_hash=entries[1].prev_hash,
            entry_hash=entries[1].entry_hash,
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[1].seq
        tlog.close()
