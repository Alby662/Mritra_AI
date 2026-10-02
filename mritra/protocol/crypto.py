"""NaCl Box encryption for the boundary protocol (plan §9.1).

DECISIONS.md (1 Oct): use NaCl ``Box`` (authenticated) instead of ``SealedBox``
so the enclave can verify which bank sent each submission.

Key pair is generated inside the enclave at boot; the public key is published
(with attestation record if Secure Execution is available).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass

from nacl.public import Box, PrivateKey, PublicKey
from nacl.utils import random as nacl_random

from mritra.protocol.messages import RoundSubmission, SealedEnvelope

logger = logging.getLogger(__name__)


@dataclass
class KeyPair:
    """An X25519 key pair."""

    private_key: PrivateKey
    public_key: PublicKey

    @classmethod
    def generate(cls) -> KeyPair:
        """Generate a fresh X25519 key pair (done inside the enclave at boot)."""
        sk = PrivateKey.generate()
        return cls(private_key=sk, public_key=sk.public_key)


def encrypt_submission(
    submission: RoundSubmission,
    sender_sk: PrivateKey,
    enclave_pk: PublicKey,
) -> SealedEnvelope:
    """Encrypt a RoundSubmission into a SealedEnvelope.

    Uses authenticated NaCl Box (X25519 + XSalsa20-Poly1305).
    """
    plaintext = submission.model_dump_json().encode("utf-8")
    payload_hash = hashlib.sha256(plaintext).hexdigest()

    box = Box(sender_sk, enclave_pk)
    nonce = nacl_random(Box.NONCE_SIZE)
    ciphertext = box.encrypt(plaintext, nonce)
    # box.encrypt returns nonce + ciphertext; extract just the ciphertext
    ct_only = ciphertext[Box.NONCE_SIZE :]

    return SealedEnvelope(
        bank_id=submission.bank_id,
        round_id=submission.round_id,
        ciphertext_b64=base64.b64encode(ct_only).decode("ascii"),
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
        payload_sha256=payload_hash,
    )


def decrypt_submission(
    envelope: SealedEnvelope,
    enclave_sk: PrivateKey,
    sender_pk: PublicKey,
) -> RoundSubmission:
    """Decrypt a SealedEnvelope back to a RoundSubmission.

    Raises ``nacl.exceptions.CryptoError`` if decryption or authentication fails.
    """
    ciphertext = base64.b64decode(envelope.ciphertext_b64)
    nonce = base64.b64decode(envelope.nonce_b64)

    box = Box(enclave_sk, sender_pk)
    plaintext = box.decrypt(ciphertext, nonce)

    payload_hash = hashlib.sha256(plaintext).hexdigest()
    if payload_hash != envelope.payload_sha256:
        raise ValueError(
            f"Payload SHA-256 mismatch: expected {envelope.payload_sha256}, got {payload_hash}"
        )

    data = json.loads(plaintext)
    return RoundSubmission(**data)


def verify_payload_hash(envelope: SealedEnvelope, plaintext: bytes) -> bool:
    """Check that the envelope's SHA-256 matches the plaintext."""
    return hashlib.sha256(plaintext).hexdigest() == envelope.payload_sha256
