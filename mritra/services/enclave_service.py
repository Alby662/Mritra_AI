"""Enclave service (plan §5 / §8.2).

The enclave:
  1. Decrypts submissions from all banks (key generated inside at boot)
  2. Reconciles cross-bank transactions (double-entry)
  3. Builds the boundary graph
  4. Computes network features (GFP on boundary graph + neighbour aggregation)
  5. Returns each bank's own accounts' network features only (rounded, logged)
  6. Logs the round in the transparency log

Labelled: "Enclave boundary simulated — production target: IBM Secure Execution"
(unless running on real Secure Execution hardware).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
from nacl.public import PrivateKey, PublicKey

from mritra.features.network import compute_network_features
from mritra.protocol.crypto import KeyPair, decrypt_submission
from mritra.protocol.messages import (
    CrossBankTxn,
    NetworkFeatures,
    RoundResponse,
    SealedEnvelope,
)
from mritra.protocol.reconcile import ReconciliationResult, reconcile_round
from mritra.protocol.tlog import TransparencyLog

logger = logging.getLogger(__name__)

# Code hash for the transparency log (hash of this file at startup)
_CODE_HASH: str | None = None


def _get_code_hash() -> str:
    global _CODE_HASH
    if _CODE_HASH is None:
        try:
            code = Path(__file__).read_bytes()
            _CODE_HASH = hashlib.sha256(code).hexdigest()
        except Exception:
            _CODE_HASH = "unknown"
    return _CODE_HASH


class EnclaveService:
    """Simulated enclave service.

    WARNING: This is a labelled simulation. In production, this would run
    inside IBM Secure Execution on LinuxONE with attestation.
    """

    SIMULATION_LABEL = (
        "Enclave boundary simulated — production target: IBM Secure Execution"
    )

    def __init__(
        self,
        tlog_path: Path,
        bank_public_keys: dict[int, PublicKey],
    ) -> None:
        # Key pair generated inside the enclave at boot
        self.keypair = KeyPair.generate()
        self.bank_public_keys = bank_public_keys
        self.tlog = TransparencyLog(tlog_path)
        logger.info(
            "Enclave booted. Public key: %s. %s",
            self.keypair.public_key.encode().hex()[:16] + "...",
            self.SIMULATION_LABEL,
        )

    @property
    def public_key(self) -> PublicKey:
        return self.keypair.public_key

    def process_round(
        self,
        round_id: int,
        envelopes: list[SealedEnvelope],
        feature_precision: int = 4,
    ) -> dict[int, RoundResponse]:
        """Process one round of submissions from all banks.

        Returns a dict mapping bank_id -> RoundResponse.
        """
        # Step 1: Decrypt all submissions
        submissions = {}
        for env in envelopes:
            sender_pk = self.bank_public_keys.get(env.bank_id)
            if sender_pk is None:
                logger.error("Unknown bank_id %d — skipping", env.bank_id)
                continue
            sub = decrypt_submission(env, self.keypair.private_key, sender_pk)
            submissions[sub.bank_id] = sub

        # Step 2: Reconcile
        all_txns: dict[int, list[CrossBankTxn]] = {}
        for bank_id, sub in submissions.items():
            all_txns[bank_id] = sub.txns
        recon = reconcile_round(all_txns)

        # Step 3: Build boundary graph
        # Collect all reconciled cross-bank edges
        import pandas as pd

        edge_rows = []
        for bank_id, sub in submissions.items():
            for txn in sub.txns:
                if txn.direction == "out":
                    edge_rows.append({
                        "edge_ref": txn.edge_ref,
                        "from_acct": f"{bank_id}_{txn.own_account}",
                        "to_acct": f"{txn.counterparty_bank}_{txn.counterparty_account}",
                        "ts": txn.ts,
                        "amount": txn.amount,
                    })
        boundary_edges = pd.DataFrame(edge_rows) if edge_rows else pd.DataFrame(
            columns=["edge_ref", "from_acct", "to_acct", "ts", "amount"]
        )

        # Step 4: Collect boundary summaries
        boundary_summaries: dict[str, np.ndarray] = {}
        for bank_id, sub in submissions.items():
            for s in sub.summaries:
                key = f"{bank_id}_{s.account}"
                boundary_summaries[key] = np.array(s.features, dtype=np.float64)

        # Step 5: Compute network features
        net_features = compute_network_features(
            boundary_edges, boundary_summaries, precision=feature_precision
        )

        # Step 6: Build responses — each bank gets only its own accounts
        responses: dict[int, RoundResponse] = {}
        for bank_id in submissions:
            prefix = f"{bank_id}_"
            bank_features = []
            for acct_key, feat_vec in net_features.items():
                if acct_key.startswith(prefix):
                    raw_acct = acct_key[len(prefix):]
                    bank_features.append(
                        NetworkFeatures(
                            round_id=round_id,
                            account=raw_acct,
                            features=feat_vec.tolist(),
                        )
                    )
            responses[bank_id] = RoundResponse(
                bank_id=bank_id,
                round_id=round_id,
                features=bank_features,
                reconciliation_mismatches=recon.total_issues,
            )

        # Step 7: Log the round
        input_hash = hashlib.sha256(
            json.dumps(
                {b: e.payload_sha256 for b, e in zip(submissions.keys(), envelopes, strict=False)},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        output_hash = hashlib.sha256(
            json.dumps(
                {b: r.model_dump_json() for b, r in responses.items()},
                sort_keys=True,
            ).encode()
        ).hexdigest()

        self.tlog.append(
            requester=f"round_{round_id}",
            query_type="boundary_exchange",
            input_sha256=input_hash,
            output_sha256=output_hash,
            enclave_code_sha256=_get_code_hash(),
        )

        logger.info(
            "Round %d: %d banks, %d boundary edges, %d net features computed, "
            "%d reconciliation issues",
            round_id,
            len(submissions),
            len(boundary_edges),
            len(net_features),
            recon.total_issues,
        )

        return responses

    def close(self) -> None:
        self.tlog.close()
