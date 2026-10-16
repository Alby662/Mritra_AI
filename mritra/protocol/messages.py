"""Pydantic v2 message schemas for the boundary protocol (plan §8).

DECISIONS.md (1 Oct): use NaCl ``Box`` (authenticated) instead of ``SealedBox``
(anonymous) so the enclave knows which bank sent a submission.  ``edge_ref`` =
dataset row_id, simulating the shared payment reference (UTR).

DECISIONS.md (16 Oct): Add ``ubo_hash`` field to ``CrossBankTxn`` and
``BoundarySummary``.  This is a salted, keyed SHA-256 hash of the Ultimate
Beneficial Owner identifier for the account.  It is computed by the bank
*before* encryption and never reveals the raw UBO name or KYC record — it is a
privacy-preserving ownership token.  The enclave uses it to detect
related-party transfers: any two boundary accounts at *different* institutions
sharing the same ``ubo_hash`` are controlled by the same beneficial owner,
making transfers between them a related-party flag under FATF R.24 / RBI PMLA.

The ``ubo_hash`` field is optional (``None`` = not provided / legacy submission)
so that existing bank nodes that have not yet upgraded their KYC pipeline remain
compatible.  The enclave treats ``None`` as "unknown ownership" and skips
related-party detection for those accounts.
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

    # ── UBO Extension (added 16 Oct) ──────────────────────────────────────
    ubo_hash: str | None = Field(
        default=None,
        description=(
            "Salted SHA-256 hash of the Ultimate Beneficial Owner identifier for "
            "own_account.  Computed as HMAC-SHA256(key=round_salt, msg=ubo_id). "
            "Never contains raw KYC data.  Used by the enclave to detect "
            "related-party transfers across institutions (same ubo_hash → same "
            "beneficial owner controlling both accounts).  None = UBO not provided."
        ),
    )


class BoundarySummary(BaseModel):
    """Locally computed feature vector for one boundary account."""

    account: str
    features: list[float] = Field(description="GFP + behavioural feature vector")
    feature_schema_version: str = "v1"

    # ── UBO Extension (added 16 Oct) ──────────────────────────────────────
    ubo_hash: str | None = Field(
        default=None,
        description=(
            "Same salted UBO hash as in CrossBankTxn — attached to the boundary "
            "summary so the enclave can resolve ownership even when an account "
            "only appears in summaries and not in any cross-bank transaction "
            "during this round."
        ),
    )


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
# Reconciliation
# ---------------------------------------------------------------------------


class ReconciliationMismatch(BaseModel):
    """A single mismatch found during double-entry reconciliation."""

    edge_ref: int
    kind: Literal["missing_counterpart", "field_mismatch"]
    fields: list[str] = Field(default_factory=list)
    bank_a: int
    bank_b: int
    value_a: str | None = None
    value_b: str | None = None


# ---------------------------------------------------------------------------
# Related-Party Detection (added 16 Oct)
# ---------------------------------------------------------------------------


class RelatedPartyFlag(BaseModel):
    """A transfer flagged as related-party due to a shared UBO hash.

    Semantics
    ---------
    When the enclave finds that ``own_account`` (belonging to ``bank_id``) and
    ``counterparty_account`` (belonging to ``counterparty_bank``) both carry the
    same ``ubo_hash``, it emits this flag in the ``RoundResponse`` for
    ``bank_id``.  The counterparty bank receives a symmetric flag in its own
    ``RoundResponse``.

    Neither bank learns the other's ``ubo_hash`` directly — they only learn that
    *their own* account's counterparty shares their beneficial owner.

    Regulatory basis
    ----------------
    * FATF Recommendation 24 — Transparency of legal persons
    * RBI Master Direction on KYC (2016, updated 2023) — beneficial ownership
    * PMLA 2002, Section 12 — reporting obligations for related-party flows
    """

    edge_ref: int = Field(description="Transaction edge_ref triggering this flag")
    own_account: str = Field(description="Bank's own account involved")
    counterparty_account: str = Field(description="Counterparty account (other institution)")
    counterparty_bank: int
    ubo_hash: str = Field(description="The shared UBO hash that triggered the flag")
    amount: float
    currency: str
    ts: int = Field(description="Unix timestamp of the transfer")
    cross_border: bool = Field(
        default=False,
        description="True when the transfer crosses a jurisdictional boundary (e.g. SWIFT)",
    )
    risk_multiplier: float = Field(
        default=1.5,
        description=(
            "Suggested risk score multiplier to apply on top of the base "
            "transaction risk score.  Cross-border related-party transfers use "
            "a higher multiplier (2.0) due to elevated FATF concern."
        ),
    )
    flag_reason: str = Field(
        default="UBO hash match across institutions",
        description="Human-readable reason for the flag, suitable for audit logs",
    )


# ---------------------------------------------------------------------------
# Enclave → Bank  (defined after RelatedPartyFlag to avoid forward reference)
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

    # ── UBO Extension (added 16 Oct) ──────────────────────────────────────
    related_party_flags: list[RelatedPartyFlag] = Field(
        default_factory=list,
        description=(
            "List of related-party flags for accounts owned by this bank. "
            "Each flag indicates a transfer to/from a counterparty account at "
            "a different institution that shares the same UBO hash. "
            "The bank receives flags ONLY for its own accounts — it cannot "
            "infer the UBO structure of other banks."
        ),
    )
