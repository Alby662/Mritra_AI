"""Tests that no outbound bank message leaks sensitive data (plan §9.5).

Asserts:
  - No outbound bank message contains a plaintext account ID from another bank
  - No internal (within-bank) edge is included
  - No labels are exposed
"""

from __future__ import annotations

import json

import pytest
from nacl.public import PrivateKey

from mritra.protocol.crypto import KeyPair, encrypt_submission
from mritra.protocol.messages import (
    BoundarySummary,
    CrossBankTxn,
    RoundSubmission,
    SealedEnvelope,
)


@pytest.fixture
def bank_keypair() -> KeyPair:
    return KeyPair.generate()


@pytest.fixture
def enclave_keypair() -> KeyPair:
    return KeyPair.generate()


class TestNoLeak:
    """Ensure no sensitive data leaks in outbound messages."""

    def test_envelope_contains_no_plaintext_account(
        self, bank_keypair, enclave_keypair
    ):
        """The SealedEnvelope's serialised form must not contain plaintext account IDs."""
        submission = RoundSubmission(
            bank_id=0,
            round_id=1,
            txns=[
                CrossBankTxn(
                    edge_ref=42,
                    own_account="SECRET_ACCOUNT_001",
                    direction="out",
                    counterparty_bank=2,
                    counterparty_account="OTHER_BANK_ACCT_999",
                    ts=1000000,
                    amount=500.0,
                    currency="USD",
                    fmt="Wire",
                )
            ],
            summaries=[
                BoundarySummary(
                    account="SECRET_ACCOUNT_001",
                    features=[1.0, 2.0, 3.0],
                )
            ],
        )
        envelope = encrypt_submission(
            submission, bank_keypair.private_key, enclave_keypair.public_key
        )

        # Check the wire-format envelope
        wire = envelope.model_dump_json()
        assert "SECRET_ACCOUNT_001" not in wire
        assert "OTHER_BANK_ACCT_999" not in wire

    def test_envelope_contains_no_labels(
        self, bank_keypair, enclave_keypair
    ):
        """Labels (is_laund) must never be in outbound messages."""
        submission = RoundSubmission(
            bank_id=0,
            round_id=1,
            txns=[
                CrossBankTxn(
                    edge_ref=1,
                    own_account="A001",
                    direction="out",
                    counterparty_bank=1,
                    counterparty_account="B001",
                    ts=100,
                    amount=100.0,
                    currency="USD",
                    fmt="Wire",
                )
            ],
            summaries=[],
        )
        envelope = encrypt_submission(
            submission, bank_keypair.private_key, enclave_keypair.public_key
        )
        wire = envelope.model_dump_json()
        assert "is_laund" not in wire
        assert "laundering" not in wire.lower()

    def test_submission_schema_has_no_label_field(self):
        """The CrossBankTxn schema must not include a label field."""
        fields = CrossBankTxn.model_fields
        forbidden_fields = {"is_laund", "is_laundering", "label", "target"}
        assert not fields.keys() & forbidden_fields

    def test_submission_schema_has_no_internal_edges(self):
        """RoundSubmission should only contain cross-bank txns, not internal ones."""
        # Verify the schema doesn't have fields for internal edges
        fields = RoundSubmission.model_fields
        assert "internal_txns" not in fields
        assert "within_bank_txns" not in fields

    def test_envelope_only_has_expected_fields(
        self, bank_keypair, enclave_keypair
    ):
        """SealedEnvelope should only expose bank_id, round_id, ciphertext, nonce, hash."""
        expected_fields = {
            "bank_id",
            "round_id",
            "ciphertext_b64",
            "nonce_b64",
            "payload_sha256",
        }
        actual_fields = set(SealedEnvelope.model_fields.keys())
        assert actual_fields == expected_fields

    def test_no_raw_balance_in_submission(self):
        """BoundarySummary should not expose raw balances."""
        fields = BoundarySummary.model_fields
        forbidden = {"balance", "raw_balance", "total_balance"}
        assert not fields.keys() & forbidden

    def test_encrypted_payload_is_not_plaintext_json(
        self, bank_keypair, enclave_keypair
    ):
        """The ciphertext should not be valid JSON (proving it's actually encrypted)."""
        import base64

        submission = RoundSubmission(
            bank_id=0,
            round_id=1,
            txns=[
                CrossBankTxn(
                    edge_ref=1,
                    own_account="A001",
                    direction="out",
                    counterparty_bank=1,
                    counterparty_account="B001",
                    ts=100,
                    amount=100.0,
                    currency="USD",
                    fmt="Wire",
                )
            ],
            summaries=[],
        )
        envelope = encrypt_submission(
            submission, bank_keypair.private_key, enclave_keypair.public_key
        )
        ct_bytes = base64.b64decode(envelope.ciphertext_b64)
        with pytest.raises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(ct_bytes)
