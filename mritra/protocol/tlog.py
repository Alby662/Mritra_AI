"""Append-only hash-chained transparency log (plan §9.3).

Schema: ``tlog(seq, ts, requester, query_type, input_sha256, output_sha256,
enclave_code_sha256, prev_hash, entry_hash)``

``entry_hash = SHA256(prev_hash || canonical_json(entry_without_hash))``
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tlog (
    seq                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  REAL    NOT NULL,
    requester           TEXT    NOT NULL,
    query_type          TEXT    NOT NULL,
    input_sha256        TEXT    NOT NULL,
    output_sha256       TEXT    NOT NULL,
    enclave_code_sha256 TEXT    NOT NULL,
    prev_hash           TEXT    NOT NULL,
    entry_hash          TEXT    NOT NULL
);
"""

GENESIS_HASH = "0" * 64  # The "previous hash" for the first entry


def _canonical_json(d: dict) -> str:
    """Deterministic JSON serialisation for hashing."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _compute_entry_hash(prev_hash: str, entry: dict) -> str:
    """SHA-256(prev_hash || canonical_json(entry without entry_hash))."""
    payload = prev_hash + _canonical_json(entry)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class LogEntry:
    """A single transparency log entry."""

    seq: int
    ts: float
    requester: str
    query_type: str
    input_sha256: str
    output_sha256: str
    enclave_code_sha256: str
    prev_hash: str
    entry_hash: str


class TransparencyLog:
    """Append-only, hash-chained SQLite transparency log."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def _last_hash(self) -> str:
        """Fetch the entry_hash of the last entry, or GENESIS_HASH."""
        row = self._conn.execute("SELECT entry_hash FROM tlog ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS_HASH

    def append(
        self,
        requester: str,
        query_type: str,
        input_sha256: str,
        output_sha256: str,
        enclave_code_sha256: str,
    ) -> LogEntry:
        """Append a new entry to the log and return it."""
        prev_hash = self._last_hash()
        ts = time.time()

        entry_dict = {
            "ts": ts,
            "requester": requester,
            "query_type": query_type,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "enclave_code_sha256": enclave_code_sha256,
            "prev_hash": prev_hash,
        }
        entry_hash = _compute_entry_hash(prev_hash, entry_dict)

        self._conn.execute(
            """INSERT INTO tlog (ts, requester, query_type, input_sha256,
               output_sha256, enclave_code_sha256, prev_hash, entry_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                requester,
                query_type,
                input_sha256,
                output_sha256,
                enclave_code_sha256,
                prev_hash,
                entry_hash,
            ),
        )
        self._conn.commit()
        seq = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return LogEntry(
            seq=seq,
            ts=ts,
            requester=requester,
            query_type=query_type,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            enclave_code_sha256=enclave_code_sha256,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )

    def entries(self) -> list[LogEntry]:
        """Return all entries in order."""
        rows = self._conn.execute(
            "SELECT seq, ts, requester, query_type, input_sha256, output_sha256, "
            "enclave_code_sha256, prev_hash, entry_hash FROM tlog ORDER BY seq"
        ).fetchall()
        return [LogEntry(*r) for r in rows]

    def close(self) -> None:
        self._conn.close()


def verify_chain(entries: list[LogEntry]) -> tuple[bool, int | None]:
    """Verify the hash chain; return (valid, first_broken_seq).

    Returns ``(True, None)`` if the chain is intact, or ``(False, seq)``
    where ``seq`` is the first entry whose hash is wrong.
    """
    prev_hash = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != prev_hash:
            return False, entry.seq

        entry_dict = {
            "ts": entry.ts,
            "requester": entry.requester,
            "query_type": entry.query_type,
            "input_sha256": entry.input_sha256,
            "output_sha256": entry.output_sha256,
            "enclave_code_sha256": entry.enclave_code_sha256,
            "prev_hash": entry.prev_hash,
        }
        expected_hash = _compute_entry_hash(prev_hash, entry_dict)
        if entry.entry_hash != expected_hash:
            return False, entry.seq

        prev_hash = entry.entry_hash

    return True, None
