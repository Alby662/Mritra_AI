"""Verify the transparency log hash chain (plan §9.3).

Usage:
    uv run python scripts/verify_log.py [path/to/tlog.db]

Recomputes the chain and reports the first broken link (if any).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mritra.protocol.tlog import TransparencyLog, verify_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the transparency log hash chain.")
    parser.add_argument(
        "db_path",
        nargs="?",
        default="results/tlog.db",
        help="Path to the transparency log SQLite database (default: results/tlog.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: {db_path} not found", file=sys.stderr)
        sys.exit(1)

    tlog = TransparencyLog(db_path)
    entries = tlog.entries()
    tlog.close()

    if not entries:
        print("Log is empty — nothing to verify.")
        sys.exit(0)

    print(f"Verifying {len(entries)} entries...")
    valid, broken_seq = verify_chain(entries)

    if valid:
        print(f"✅ Chain intact. {len(entries)} entries, head = {entries[-1].entry_hash[:16]}...")
        sys.exit(0)
    else:
        print(f"❌ Chain broken at seq {broken_seq}")
        for e in entries:
            if e.seq == broken_seq:
                print(f"   Entry: seq={e.seq} ts={e.ts} requester={e.requester}")
                print(f"   prev_hash={e.prev_hash[:16]}...")
                print(f"   entry_hash={e.entry_hash[:16]}...")
                break
        sys.exit(1)


if __name__ == "__main__":
    main()
