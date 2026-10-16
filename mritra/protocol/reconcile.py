"""Double-entry reconciliation of cross-bank transactions (plan §8.2 step 2).

Each cross-bank transaction is reported by both the sending and receiving bank.
The enclave matches reports by ``edge_ref`` and verifies that the key fields
agree: amount, timestamp, currency.  Mismatches are flagged and logged.

16 Oct — Related-party detection pass added (``detect_related_party_flags``).

After the standard double-entry reconciliation, the enclave performs a second
pass over all *matched* transactions.  If both sides of a matched transaction
carry a non-None ``ubo_hash`` and those hashes are equal, the transfer is
flagged as a related-party transaction: the same beneficial owner controls
accounts on both sides of what appeared to be an arm's-length commercial
payment.

Privacy guarantee: the enclave never emits the raw ``ubo_hash`` to the wrong
bank.  Bank A only learns that *its own* account's counterparty shares the same
UBO — it does not learn the UBO hash of Bank B's other accounts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from mritra.protocol.messages import (
    CrossBankTxn,
    ReconciliationMismatch,
    RelatedPartyFlag,
)

logger = logging.getLogger(__name__)

# Cross-border payment format prefixes — used to set the cross_border flag.
# In production this would be determined by jurisdiction metadata on the txn.
_CROSS_BORDER_FMTS = frozenset({"SWIFT", "SEPA_CROSS", "WIRE_INTL", "IMPS_INTL"})

# Risk multipliers for related-party flags.
_RISK_MULTIPLIER_DOMESTIC = 1.5
_RISK_MULTIPLIER_CROSS_BORDER = 2.0


@dataclass
class ReconciliationResult:
    """Outcome of reconciling one round of cross-bank transactions."""

    matched: int = 0
    matched_refs: list[int] = field(default_factory=list)
    mismatches: list[ReconciliationMismatch] = field(default_factory=list)
    unmatched_refs: list[int] = field(default_factory=list)

    # ── Related-party detection output (added 16 Oct) ─────────────────────
    # Keyed by bank_id so the enclave can partition delivery: each bank only
    # receives flags for its own accounts.
    related_party_flags_by_bank: dict[int, list[RelatedPartyFlag]] = field(
        default_factory=dict
    )

    @property
    def total_issues(self) -> int:
        return len(self.mismatches) + len(self.unmatched_refs)

    @property
    def mismatched_refs(self) -> set[int]:
        """edge_refs with >=1 field mismatch -- NOT matched, even though both sides
        reported them (PROTOCOL.md §6 step 3: matched requires identical fields)."""
        return {m.edge_ref for m in self.mismatches}

    @property
    def total_related_party_flags(self) -> int:
        """Total number of related-party flags across all banks."""
        return sum(len(flags) for flags in self.related_party_flags_by_bank.values())


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
    ReconciliationResult with matched count, mismatches, unmatched refs, and
    related-party flags partitioned by bank_id.
    """
    result = ReconciliationResult()

    # Index by edge_ref -> list of (bank_id, txn)
    by_ref: dict[int, list[tuple[int, CrossBankTxn]]] = {}
    for bank_id, txns in submissions.items():
        for txn in txns:
            by_ref.setdefault(txn.edge_ref, []).append((bank_id, txn))

    # ── Step 1: Standard double-entry reconciliation ──────────────────────
    matched_pairs: list[tuple[int, CrossBankTxn, int, CrossBankTxn]] = []

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
                    bank_b=txn.counterparty_bank,
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
            matched_pairs.append((bank_a, txn_a, bank_b, txn_b))

    logger.info(
        "Reconciliation: matched=%d mismatches=%d unmatched=%d",
        result.matched,
        len(result.mismatches),
        len(result.unmatched_refs),
    )

    # ── Step 2: Related-party detection pass ──────────────────────────────
    rp_flags = detect_related_party_flags(matched_pairs)
    result.related_party_flags_by_bank = rp_flags

    if rp_flags:
        total = sum(len(v) for v in rp_flags.values())
        logger.info(
            "Related-party detection: %d flag(s) across %d institution(s)",
            total,
            len(rp_flags),
        )

    return result


def detect_related_party_flags(
    matched_pairs: list[tuple[int, CrossBankTxn, int, CrossBankTxn]],
) -> dict[int, list[RelatedPartyFlag]]:
    """Detect related-party transfers among matched transaction pairs.

    A related-party transfer is one where both sides carry the same non-None
    ``ubo_hash``.  This means the same Ultimate Beneficial Owner controls
    accounts at two different institutions, and is moving money between them —
    a layering technique used to obscure the beneficial owner of funds.

    Parameters
    ----------
    matched_pairs : list of (bank_a, txn_a, bank_b, txn_b)
        Fully reconciled transaction pairs from the double-entry pass.

    Returns
    -------
    dict mapping bank_id -> list[RelatedPartyFlag]
        Flags partitioned by the receiving bank for isolated delivery.
        Each bank receives flags ONLY for its own accounts.
    """
    flags_by_bank: dict[int, list[RelatedPartyFlag]] = {}

    for bank_a, txn_a, bank_b, txn_b in matched_pairs:
        # Skip if either side has no UBO hash (legacy or opted-out submission)
        if txn_a.ubo_hash is None or txn_b.ubo_hash is None:
            continue

        # Skip if they don't share the same beneficial owner
        if txn_a.ubo_hash != txn_b.ubo_hash:
            continue

        # Both sides share a UBO hash → related-party transfer
        shared_hash = txn_a.ubo_hash
        is_cross_border = (
            txn_a.fmt.upper() in _CROSS_BORDER_FMTS
            or txn_b.fmt.upper() in _CROSS_BORDER_FMTS
        )
        multiplier = (
            _RISK_MULTIPLIER_CROSS_BORDER if is_cross_border
            else _RISK_MULTIPLIER_DOMESTIC
        )
        flag_reason = (
            f"UBO hash match across Bank {bank_a} and Bank {bank_b} "
            f"({'cross-border' if is_cross_border else 'domestic'} transfer)"
        )

        # Flag for Bank A — tells Bank A that its own account's counterparty
        # at Bank B shares the same beneficial owner
        flag_for_a = RelatedPartyFlag(
            edge_ref=txn_a.edge_ref,
            own_account=txn_a.own_account,
            counterparty_account=txn_a.counterparty_account,
            counterparty_bank=bank_b,
            ubo_hash=shared_hash,
            amount=txn_a.amount,
            currency=txn_a.currency,
            ts=txn_a.ts,
            cross_border=is_cross_border,
            risk_multiplier=multiplier,
            flag_reason=flag_reason,
        )
        flags_by_bank.setdefault(bank_a, []).append(flag_for_a)

        # Symmetric flag for Bank B — tells Bank B the same thing from its side
        flag_for_b = RelatedPartyFlag(
            edge_ref=txn_b.edge_ref,
            own_account=txn_b.own_account,
            counterparty_account=txn_b.counterparty_account,
            counterparty_bank=bank_a,
            ubo_hash=shared_hash,
            amount=txn_b.amount,
            currency=txn_b.currency,
            ts=txn_b.ts,
            cross_border=is_cross_border,
            risk_multiplier=multiplier,
            flag_reason=flag_reason,
        )
        flags_by_bank.setdefault(bank_b, []).append(flag_for_b)

        logger.debug(
            "Related-party flag: edge_ref=%d bank_a=%d bank_b=%d ubo_hash=%s cross_border=%s",
            txn_a.edge_ref,
            bank_a,
            bank_b,
            shared_hash,
            is_cross_border,
        )

    return flags_by_bank
