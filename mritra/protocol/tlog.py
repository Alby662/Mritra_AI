"""Append-only hash-chained transparency log (plan §9.3).

Schema: ``tlog(seq, ts, type, actor, round_id, input_sha256, output_sha256,
code_sha256, prev_hash, entry_hash)``

``entry_hash = SHA256(prev_hash || canonical_json(entry_without_hash))``
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tlog (
    seq                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  INTEGER NOT NULL,
    type                TEXT    NOT NULL,
    actor               TEXT    NOT NULL,
    round_id            INTEGER,
    input_sha256        TEXT,
    output_sha256       TEXT,
    detail              TEXT    NOT NULL DEFAULT '{}',
    code_sha256         TEXT    NOT NULL,
    prev_hash           TEXT    NOT NULL,
    entry_hash          TEXT    NOT NULL
);
"""

GENESIS_HASH = "0" * 64


def _canonical_json(d: dict) -> str:
    """Deterministic JSON serialisation for hashing."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_entry_hash(prev_hash: str, entry: dict) -> str:
    """SHA-256(prev_hash || canonical_json(entry without entry_hash))."""
    payload = prev_hash + _canonical_json(entry)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class LogEntry:
    """A single transparency log entry."""

    seq: int
    ts: int
    type: str
    actor: str
    round_id: int | None
    input_sha256: str | None
    output_sha256: str | None
    code_sha256: str
    prev_hash: str
    entry_hash: str
    detail: dict = field(default_factory=dict)


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
        type: str,
        actor: str,
        code_sha256: str,
        round_id: int | None = None,
        input_sha256: str | None = None,
        output_sha256: str | None = None,
        detail: dict | None = None,
    ) -> LogEntry:
        prev_hash = self._last_hash()
        ts = int(time.time())
        detail = detail or {}
        detail_json = _canonical_json(detail)

        entry_dict = {
            "ts": ts,
            "type": type,
            "actor": actor,
            "round_id": round_id,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "code_sha256": code_sha256,
            "detail": detail,
            "prev_hash": prev_hash,
        }

        entry_hash = _compute_entry_hash(prev_hash, entry_dict)

        self._conn.execute(
            """INSERT INTO tlog (ts, type, actor, round_id, input_sha256,
               output_sha256, code_sha256, detail, prev_hash, entry_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                type,
                actor,
                round_id,
                input_sha256,
                output_sha256,
                code_sha256,
                detail_json,
                prev_hash,
                entry_hash,
            ),
        )
        self._conn.commit()
        seq = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return LogEntry(
            seq=seq,
            ts=ts,
            type=type,
            actor=actor,
            round_id=round_id,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            code_sha256=code_sha256,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            detail=detail,
        )

    def entries(self) -> list[LogEntry]:
        rows = self._conn.execute(
            "SELECT seq, ts, type, actor, round_id, input_sha256, output_sha256, "
            "code_sha256, detail, prev_hash, entry_hash FROM tlog ORDER BY seq"
        ).fetchall()
        return [
            LogEntry(
                seq=r[0],
                ts=r[1],
                type=r[2],
                actor=r[3],
                round_id=r[4],
                input_sha256=r[5],
                output_sha256=r[6],
                code_sha256=r[7],
                detail=json.loads(r[8]),
                prev_hash=r[9],
                entry_hash=r[10],
            )
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()


def verify_chain(entries: list[LogEntry]) -> tuple[bool, int | None]:
    prev_hash = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != prev_hash:
            return False, entry.seq

        entry_dict = {
            "ts": entry.ts,
            "type": entry.type,
            "actor": entry.actor,
            "round_id": entry.round_id,
            "input_sha256": entry.input_sha256,
            "output_sha256": entry.output_sha256,
            "code_sha256": entry.code_sha256,
            "detail": entry.detail,
            "prev_hash": entry.prev_hash,
        }
        expected_hash = _compute_entry_hash(prev_hash, entry_dict)
        if entry.entry_hash != expected_hash:
            return False, entry.seq

        prev_hash = entry.entry_hash

    return True, None
