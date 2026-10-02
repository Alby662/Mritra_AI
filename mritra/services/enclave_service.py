"""Enclave service (plan §5 / §8.2).

The enclave:
  1. Decrypts submissions from all banks (key generated inside at boot)
  2. Reconciles cross-bank transactions (double-entry)
  3. Accumulates this round's edges into the persistent boundary graph
     (PROTOCOL.md §6 step 4: "persistent across rounds, inside the enclave")
     and updates each account's latest summary vector
  4. Computes network features from the accumulated graph, restricted to
     ts < as_of (CLAUDE.md §4 / PREREGISTRATION.md §4: round-granularity
     causality) -- never from only this round's edges in isolation
  5. Returns each bank's own accounts that appeared this round (rounded, logged)
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
import pandas as pd
from nacl.public import PublicKey

from mritra.features.network import compute_network_features
from mritra.protocol.crypto import KeyPair, decrypt_submission
from mritra.protocol.messages import (
    CrossBankTxn,
    NetworkFeatures,
    RoundResponse,
    SealedEnvelope,
)
from mritra.protocol.reconcile import reconcile_round
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

    SIMULATION_LABEL = "Enclave boundary simulated — production target: IBM Secure Execution"

    _EDGE_COLUMNS = ["edge_ref", "from_acct", "to_acct", "ts", "amount"]

    def __init__(
        self,
        tlog_path: Path,
        bank_public_keys: dict[int, PublicKey],
    ) -> None:
        # Key pair generated inside the enclave at boot
        self.keypair = KeyPair.generate()
        self.bank_public_keys = bank_public_keys
        self.tlog = TransparencyLog(tlog_path)

        # Persistent boundary graph state (PROTOCOL.md §6 step 4), accumulated across
        # every process_round() call on this instance for as long as it lives.
        self._boundary_edges = pd.DataFrame(columns=self._EDGE_COLUMNS)
        self._latest_summaries: dict[str, np.ndarray] = {}

        logger.info(
            "Enclave booted. Public key: %s. %s",
            self.keypair.public_key.encode().hex()[:16] + "...",
            self.SIMULATION_LABEL,
        )

    @property
    def public_key(self) -> PublicKey:
        return self.keypair.public_key

    @property
    def boundary_edge_count(self) -> int:
        """Total edges accumulated in the persistent boundary graph so far."""
        return len(self._boundary_edges)

    def process_round(
        self,
        round_id: int,
        envelopes: list[SealedEnvelope],
        as_of: int,
        feature_precision: int = 4,
    ) -> dict[int, RoundResponse]:
        """Process one round of submissions from all banks.

        Parameters
        ----------
        as_of : int
            This round's exclusive timestamp cutoff (its ``window_end``,
            PROTOCOL.md §6); forwarded to ``compute_network_features`` so a
            round can never be computed from a transaction at or after it.

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

        # Step 3: This round's edges, appended to the persistent boundary graph
        # (PROTOCOL.md §6 step 4). edge_rows are this round's edges only; accounts_this_round
        # is used in step 6 to limit the response to accounts that appeared this round, per
        # the same step's output-minimisation rule -- the FEATURES in step 4 are computed
        # from the full accumulated graph, but what's released is round-scoped.
        edge_rows = []
        accounts_this_round: set[str] = set()
        for bank_id, sub in submissions.items():
            for txn in sub.txns:
                from_key = f"{bank_id}_{txn.own_account}"
                to_key = f"{txn.counterparty_bank}_{txn.counterparty_account}"
                accounts_this_round.add(from_key)
                accounts_this_round.add(to_key)
                if txn.direction == "out":
                    edge_rows.append(
                        {
                            "edge_ref": txn.edge_ref,
                            "from_acct": from_key,
                            "to_acct": to_key,
                            "ts": txn.ts,
                            "amount": txn.amount,
                        }
                    )
        if edge_rows:
            new_edges = pd.DataFrame(edge_rows)
            self._boundary_edges = (
                new_edges
                if self._boundary_edges.empty
                else pd.concat([self._boundary_edges, new_edges], ignore_index=True)
            )

        # Step 4: latest per-account summary (PROTOCOL.md §6 step 4: "latest summary
        # vector"); a bank's new submission for an account replaces its previous one.
        for bank_id, sub in submissions.items():
            for s in sub.summaries:
                key = f"{bank_id}_{s.account}"
                self._latest_summaries[key] = np.array(s.features, dtype=np.float64)

        # Step 5: compute network features from the ACCUMULATED graph, restricted to
        # ts < as_of. compute_network_features's own ValueError guard still enforces this
        # even though self._boundary_edges should never itself hold a ts >= as_of (every
        # round's edges satisfy ts < that round's own as_of, and as_of is non-decreasing
        # across rounds in normal use).
        edges_up_to_as_of = self._boundary_edges[self._boundary_edges["ts"] < as_of]
        net_features = compute_network_features(
            edges_up_to_as_of, self._latest_summaries, as_of=as_of, precision=feature_precision
        )

        # Step 6: Build responses — each bank gets only its own accounts that appeared
        # this round (PROTOCOL.md §6 step 6), even though their features reflect the full
        # accumulated graph.
        responses: dict[int, RoundResponse] = {}
        for bank_id in submissions:
            prefix = f"{bank_id}_"
            bank_features = []
            for acct_key, feat_vec in net_features.items():
                if acct_key.startswith(prefix) and acct_key in accounts_this_round:
                    raw_acct = acct_key[len(prefix) :]
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
            "Round %d: %d banks, %d new edges (%d accumulated), %d net features computed, "
            "%d reconciliation issues",
            round_id,
            len(submissions),
            len(edge_rows),
            len(self._boundary_edges),
            len(net_features),
            recon.total_issues,
        )

        return responses

    def close(self) -> None:
        self.tlog.close()
