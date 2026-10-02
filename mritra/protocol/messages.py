"""Pydantic v2 message schemas for the boundary protocol (plan §8).

DECISIONS.md (1 Oct): use NaCl ``Box`` (authenticated) instead of ``SealedBox``
(anonymous) so the enclave knows which bank sent a submission.  ``edge_ref`` =
dataset row_id, simulating the shared payment reference (UTR).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Bank → Enclave
# ---------------------------------------------------------------------------


class CrossBankTxn(BaseModel):
    """A single cross-bank transaction reported by a bank."""

    edge_ref: int = Field(description="Dataset row_id; simulates shared UTR")
    own_account: str = Field(description="Raw account ID — only readable inside enclave")
    direction: Literal["out", "in"]
    counterparty_bank: int
    counterparty_account: str
    ts: int = Field(description="Unix seconds")
    amount: float
    currency: str
    fmt: str = Field(description="Payment format")


class BoundarySummary(BaseModel):
    """Locally computed feature vector for one boundary account."""

    account: str
    features: list[float] = Field(description="GFP + behavioural feature vector")
    feature_schema_version: str = "v1"


class RoundSubmission(BaseModel):
    """A bank's full submission for one round."""

    bank_id: int
    round_id: int
    txns: list[CrossBankTxn]
    summaries: list[BoundarySummary]


class SealedEnvelope(BaseModel):
    """What actually travels on the wire (encrypted)."""

    bank_id: int
    round_id: int
    ciphertext_b64: str = Field(description="NaCl Box encrypted JSON")
    nonce_b64: str = Field(description="NaCl nonce for decryption")
    payload_sha256: str = Field(description="SHA-256 of plaintext, for the log")


# ---------------------------------------------------------------------------
# Enclave → Bank
# ---------------------------------------------------------------------------


class NetworkFeatures(BaseModel):
    """Network features returned by the enclave to a bank for its own accounts."""

    round_id: int
    account: str
    features: list[float]
    schema_version: str = "v1"


class RoundResponse(BaseModel):
    """Enclave response to a bank for one round."""

    bank_id: int
    round_id: int
    features: list[NetworkFeatures]
    reconciliation_mismatches: int = 0


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


class ReconciliationMismatch(BaseModel):
    """A single mismatch found during double-entry reconciliation."""

    edge_ref: int
    field: str = Field(description="Which field mismatched (amount, ts, etc.)")
    bank_a: int
    bank_b: int
    value_a: str
    value_b: str
