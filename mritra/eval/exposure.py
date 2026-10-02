"""Data exposure metric (plan §10).

Fields and bytes crossing a boundary per round — measures what each
configuration reveals outside the bank.
"""

from __future__ import annotations

import logging
from typing import Any

from mritra.protocol.messages import RoundSubmission

logger = logging.getLogger(__name__)


def measure_exposure(submission: RoundSubmission) -> dict[str, Any]:
    """Measure data exposure for a single round submission.

    Returns the fields that cross the boundary, counts, and byte sizes.
    """
    payload = submission.model_dump_json().encode("utf-8")

    txn_fields = set()
    for txn in submission.txns:
        txn_fields.update(txn.model_fields.keys())

    summary_fields = set()
    for s in submission.summaries:
        summary_fields.update(s.model_fields.keys())

    return {
        "bank_id": submission.bank_id,
        "round_id": submission.round_id,
        "n_cross_txns": len(submission.txns),
        "n_boundary_summaries": len(submission.summaries),
        "txn_fields_crossing": sorted(txn_fields),
        "summary_fields_crossing": sorted(summary_fields),
        "payload_bytes": len(payload),
        "fields_never_crossing": [
            "internal_edges",
            "non_boundary_accounts",
            "labels",
            "raw_balances",
        ],
    }


def aggregate_exposure(
    round_exposures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate exposure across rounds and banks."""
    if not round_exposures:
        return {"total_rounds": 0}

    total_txns = sum(r["n_cross_txns"] for r in round_exposures)
    total_summaries = sum(r["n_boundary_summaries"] for r in round_exposures)
    total_bytes = sum(r["payload_bytes"] for r in round_exposures)
    n_rounds = len(round_exposures)

    return {
        "total_rounds": n_rounds,
        "total_cross_txns_sent": total_txns,
        "total_boundary_summaries_sent": total_summaries,
        "total_payload_bytes": total_bytes,
        "avg_bytes_per_round": total_bytes / n_rounds,
        "avg_txns_per_round": total_txns / n_rounds,
        "fields_crossing_boundary": round_exposures[0]["txn_fields_crossing"],
        "fields_never_crossing": round_exposures[0]["fields_never_crossing"],
    }
