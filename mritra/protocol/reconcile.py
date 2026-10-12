"""Double-entry reconciliation of cross-bank transactions (plan §8.2 step 2).

Each cross-bank transaction is reported by both the sending and receiving bank.
The enclave matches reports by ``edge_ref`` and verifies that the key fields
agree: amount, timestamp, currency.  Mismatches are flagged and logged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from mritra.protocol.messages import CrossBankTxn, ReconciliationMismatch

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Outcome of reconciling one round of cross-bank transactions."""

    matched: int = 0
    matched_refs: list[int] = field(default_factory=list)
    mismatches: list[ReconciliationMismatch] = field(default_factory=list)
    unmatched_refs: list[int] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.mismatches) + len(self.unmatched_refs)

    @property
    def mismatched_refs(self) -> set[int]:
        """edge_refs with >=1 field mismatch -- NOT matched, even though both sides
        reported them (PROTOCOL.md §6 step 3: matched requires identical fields)."""
        return {m.edge_ref for m in self.mismatches}


def reconcile_round(
    submissions: dict[int, list[CrossBankTxn]],
    amount_tolerance: float = 0.0,
) -> ReconciliationResult:
    """Reconcile cross-bank transactions from all banks for one round.

    Parameters
    ----------
    submissions : dict
        Mapping of ``bank_id`` -> list of ``CrossBankTxn`` from that bank.
    amount_tolerance : float
        Maximum allowed difference in amount before flagging a mismatch.

    Returns
    -------
    ReconciliationResult with matched count, mismatches, and unmatched refs.
    """
    result = ReconciliationResult()

    # Index by edge_ref -> list of (bank_id, txn)
    by_ref: dict[int, list[tuple[int, CrossBankTxn]]] = {}
    for bank_id, txns in submissions.items():
        for txn in txns:
            by_ref.setdefault(txn.edge_ref, []).append((bank_id, txn))

    for edge_ref, reports in by_ref.items():
        if len(reports) < 2:
            result.unmatched_refs.append(edge_ref)
            bank_id, txn = reports[0]
            result.mismatches.append(
                ReconciliationMismatch(
                    edge_ref=edge_ref,
                    kind="missing_counterpart",
                    fields=[],
                    bank_a=bank_id,
                    bank_b=txn.counterparty_bank
                )
            )
            continue

        if len(reports) > 2:
            logger.warning(
                "edge_ref=%d reported by %d banks (expected 2)",
                edge_ref,
                len(reports),
            )

        # Compare the first two reports
        bank_a, txn_a = reports[0]
        bank_b, txn_b = reports[1]

        mismatched_fields = []

        # Check amount
        if abs(txn_a.amount - txn_b.amount) > amount_tolerance:
            mismatched_fields.append("amount")

        # Check timestamp
        if txn_a.ts != txn_b.ts:
            mismatched_fields.append("ts")

        # Check currency
        if txn_a.currency != txn_b.currency:
            mismatched_fields.append("currency")

        if mismatched_fields:
            result.mismatches.append(
                ReconciliationMismatch(
                    edge_ref=edge_ref,
                    kind="field_mismatch",
                    fields=mismatched_fields,
                    bank_a=bank_a,
                    bank_b=bank_b,
                    value_a=str(txn_a.amount) if "amount" in mismatched_fields else None,
                    value_b=str(txn_b.amount) if "amount" in mismatched_fields else None,
                )
            )
            
        else:
            result.matched += 1
            result.matched_refs.append(edge_ref)

    logger.info(
        "Reconciliation: matched=%d mismatches=%d unmatched=%d",
        result.matched,
        len(result.mismatches),
        len(result.unmatched_refs),
    )
    return result
