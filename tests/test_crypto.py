"""Tests for the NaCl Box crypto layer (plan §9.5).

Asserts:
  - Only the enclave key decrypts
  - Tampered ciphertext fails
  - Payload SHA-256 is verified
"""

from __future__ import annotations

import base64

import pytest
from nacl.exceptions import CryptoError

from mritra.protocol.crypto import (
    KeyPair,
    decrypt_submission,
    encrypt_submission,
    verify_payload_hash,
)
from mritra.protocol.messages import CrossBankTxn, RoundSubmission


@pytest.fixture
def bank_keypair() -> KeyPair:
    return KeyPair.generate()


@pytest.fixture
def enclave_keypair() -> KeyPair:
    return KeyPair.generate()


@pytest.fixture
def sample_submission() -> RoundSubmission:
    return RoundSubmission(
        bank_id=0,
        round_id=1,
        txns=[
            CrossBankTxn(
                edge_ref=42,
                own_account="A001",
                direction="out",
                counterparty_bank=2,
                counterparty_account="B002",
                ts=1000000,
                amount=500.0,
                currency="USD",
                fmt="Wire",
            )
        ],
        summaries=[],
    )


class TestEncryptDecrypt:
    """Round-trip encryption and decryption."""

    def test_roundtrip(self, bank_keypair, enclave_keypair, sample_submission):
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        result = decrypt_submission(
            envelope,
            enclave_keypair.private_key,
            bank_keypair.public_key,
        )
        assert result.bank_id == sample_submission.bank_id
        assert result.round_id == sample_submission.round_id
        assert len(result.txns) == 1
        assert result.txns[0].edge_ref == 42

    def test_only_enclave_key_decrypts(self, bank_keypair, enclave_keypair, sample_submission):
        """A different key pair cannot decrypt the envelope."""
        wrong_keypair = KeyPair.generate()
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        with pytest.raises(CryptoError):
            decrypt_submission(
                envelope,
                wrong_keypair.private_key,
                bank_keypair.public_key,
            )

    def test_wrong_sender_key_fails(self, bank_keypair, enclave_keypair, sample_submission):
        """Decrypting with wrong sender public key fails."""
        wrong_sender = KeyPair.generate()
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        with pytest.raises(CryptoError):
            decrypt_submission(
                envelope,
                enclave_keypair.private_key,
                wrong_sender.public_key,
            )


class TestTamperDetection:
    """Tampered ciphertext must fail."""

    def test_tampered_ciphertext_fails(self, bank_keypair, enclave_keypair, sample_submission):
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        # Tamper with ciphertext
        ct_bytes = bytearray(base64.b64decode(envelope.ciphertext_b64))
        ct_bytes[0] ^= 0xFF  # flip bits
        envelope.ciphertext_b64 = base64.b64encode(bytes(ct_bytes)).decode()

        with pytest.raises(CryptoError):
            decrypt_submission(
                envelope,
                enclave_keypair.private_key,
                bank_keypair.public_key,
            )

    def test_tampered_nonce_fails(self, bank_keypair, enclave_keypair, sample_submission):
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        nonce_bytes = bytearray(base64.b64decode(envelope.nonce_b64))
        nonce_bytes[0] ^= 0xFF
        envelope.nonce_b64 = base64.b64encode(bytes(nonce_bytes)).decode()

        with pytest.raises(CryptoError):
            decrypt_submission(
                envelope,
                enclave_keypair.private_key,
                bank_keypair.public_key,
            )


class TestPayloadHash:
    """SHA-256 of plaintext is verified."""

    def test_payload_hash_matches(self, bank_keypair, enclave_keypair, sample_submission):
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        plaintext = sample_submission.model_dump_json().encode("utf-8")
        assert verify_payload_hash(envelope, plaintext) is True

    def test_wrong_payload_hash_detected(self, bank_keypair, enclave_keypair, sample_submission):
        envelope = encrypt_submission(
            sample_submission,
            bank_keypair.private_key,
            enclave_keypair.public_key,
        )
        # Tamper with the hash
        envelope.payload_sha256 = "0" * 64

        # Decryption succeeds but hash verification should fail;
        # the decrypt_submission function checks the hash internally
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            decrypt_submission(
                envelope,
                enclave_keypair.private_key,
                bank_keypair.public_key,
            )
