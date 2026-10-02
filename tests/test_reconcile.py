"""Tests for double-entry reconciliation (plan §9.5).

Asserts: injected mismatches are detected.
"""

from __future__ import annotations

import pytest

from mritra.protocol.messages import CrossBankTxn
from mritra.protocol.reconcile import reconcile_round


def _make_txn(
    edge_ref: int = 1,
    own_account: str = "A001",
    direction: str = "out",
    counterparty_bank: int = 2,
    counterparty_account: str = "B002",
    ts: int = 1000000,
    amount: float = 500.0,
    currency: str = "USD",
    fmt: str = "Wire",
) -> CrossBankTxn:
    return CrossBankTxn(
        edge_ref=edge_ref,
        own_account=own_account,
        direction=direction,
        counterparty_bank=counterparty_bank,
        counterparty_account=counterparty_account,
        ts=ts,
        amount=amount,
        currency=currency,
        fmt=fmt,
    )


class TestReconciliation:
    """Double-entry reconciliation tests."""

    def test_matching_reports(self):
        """Two banks reporting the same transaction should match."""
        bank_0_txn = _make_txn(edge_ref=1, direction="out", amount=500.0)
        bank_1_txn = _make_txn(edge_ref=1, direction="in", amount=500.0)
        result = reconcile_round({0: [bank_0_txn], 1: [bank_1_txn]})
        assert result.matched == 1
        assert len(result.mismatches) == 0
        assert len(result.unmatched_refs) == 0

    def test_amount_mismatch_detected(self):
        """Different amounts on the same edge_ref should be flagged."""
        bank_0_txn = _make_txn(edge_ref=1, amount=500.0)
        bank_1_txn = _make_txn(edge_ref=1, amount=450.0)
        result = reconcile_round({0: [bank_0_txn], 1: [bank_1_txn]})
        assert result.matched == 0
        assert len(result.mismatches) == 1
        assert result.mismatches[0].field == "amount"

    def test_timestamp_mismatch_detected(self):
        """Different timestamps should be flagged."""
        bank_0_txn = _make_txn(edge_ref=1, ts=1000000)
        bank_1_txn = _make_txn(edge_ref=1, ts=1000001)
        result = reconcile_round({0: [bank_0_txn], 1: [bank_1_txn]})
        assert any(m.field == "ts" for m in result.mismatches)

    def test_currency_mismatch_detected(self):
        """Different currencies should be flagged."""
        bank_0_txn = _make_txn(edge_ref=1, currency="USD")
        bank_1_txn = _make_txn(edge_ref=1, currency="EUR")
        result = reconcile_round({0: [bank_0_txn], 1: [bank_1_txn]})
        assert any(m.field == "currency" for m in result.mismatches)

    def test_unmatched_ref_detected(self):
        """A transaction reported by only one bank should be unmatched."""
        bank_0_txn = _make_txn(edge_ref=1)
        result = reconcile_round({0: [bank_0_txn]})
        assert result.matched == 0
        assert 1 in result.unmatched_refs

    def test_multiple_mismatches_on_same_edge(self):
        """Multiple field mismatches on the same edge should all be reported."""
        bank_0_txn = _make_txn(edge_ref=1, amount=500.0, ts=1000000, currency="USD")
        bank_1_txn = _make_txn(edge_ref=1, amount=450.0, ts=1000001, currency="EUR")
        result = reconcile_round({0: [bank_0_txn], 1: [bank_1_txn]})
        fields = {m.field for m in result.mismatches}
        assert fields == {"amount", "ts", "currency"}

    def test_amount_tolerance(self):
        """Amount within tolerance should match."""
        bank_0_txn = _make_txn(edge_ref=1, amount=500.0)
        bank_1_txn = _make_txn(edge_ref=1, amount=500.005)
        result = reconcile_round(
            {0: [bank_0_txn], 1: [bank_1_txn]}, amount_tolerance=0.01
        )
        assert not any(m.field == "amount" for m in result.mismatches)

    def test_mixed_batch(self):
        """Mix of matching, mismatching, and unmatched transactions."""
        submissions = {
            0: [
                _make_txn(edge_ref=1, amount=500.0),  # matches
                _make_txn(edge_ref=2, amount=300.0),  # amount mismatch
                _make_txn(edge_ref=3, amount=200.0),  # unmatched
            ],
            1: [
                _make_txn(edge_ref=1, amount=500.0),  # matches
                _make_txn(edge_ref=2, amount=250.0),  # amount mismatch
            ],
        }
        result = reconcile_round(submissions)
        assert result.matched == 1
        assert len(result.mismatches) == 1
        assert 3 in result.unmatched_refs
