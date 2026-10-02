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
    mismatches: list[ReconciliationMismatch] = field(default_factory=list)
    unmatched_refs: list[int] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.mismatches) + len(self.unmatched_refs)


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

        matched = True

        # Check amount
        if abs(txn_a.amount - txn_b.amount) > amount_tolerance:
            result.mismatches.append(
                ReconciliationMismatch(
                    edge_ref=edge_ref,
                    field="amount",
                    bank_a=bank_a,
                    bank_b=bank_b,
                    value_a=str(txn_a.amount),
                    value_b=str(txn_b.amount),
                )
            )
            matched = False

        # Check timestamp
        if txn_a.ts != txn_b.ts:
            result.mismatches.append(
                ReconciliationMismatch(
                    edge_ref=edge_ref,
                    field="ts",
                    bank_a=bank_a,
                    bank_b=bank_b,
                    value_a=str(txn_a.ts),
                    value_b=str(txn_b.ts),
                )
            )
            matched = False

        # Check currency
        if txn_a.currency != txn_b.currency:
            result.mismatches.append(
                ReconciliationMismatch(
                    edge_ref=edge_ref,
                    field="currency",
                    bank_a=bank_a,
                    bank_b=bank_b,
                    value_a=txn_a.currency,
                    value_b=txn_b.currency,
                )
            )
            matched = False

        if matched:
            result.matched += 1

    logger.info(
        "Reconciliation: matched=%d mismatches=%d unmatched=%d",
        result.matched,
        len(result.mismatches),
        len(result.unmatched_refs),
    )
    return result
