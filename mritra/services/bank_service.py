"""Bank service: local scoring + boundary exchange (plan §5 / §8).

Each bank:
  1. Computes local features (GFP + behavioural) on its own transaction view
  2. Identifies boundary accounts (those with cross-institution transactions)
  3. Encrypts cross-bank transactions + boundary summaries to the enclave
  4. Receives back network features for its own accounts
  5. Re-scores with the augmented feature set (C3 configuration)
"""

from __future__ import annotations

import logging

import pandas as pd
from nacl.public import PrivateKey, PublicKey

from mritra.protocol.crypto import encrypt_submission
from mritra.protocol.messages import (
    BoundarySummary,
    CrossBankTxn,
    NetworkFeatures,
    RoundSubmission,
    SealedEnvelope,
)

logger = logging.getLogger(__name__)


class BankService:
    """Simulated bank service for one institution."""

    def __init__(
        self,
        bank_id: int,
        private_key: PrivateKey,
        enclave_public_key: PublicKey,
    ) -> None:
        self.bank_id = bank_id
        self.private_key = private_key
        self.public_key = private_key.public_key
        self.enclave_public_key = enclave_public_key

    def identify_boundary_accounts(self, df: pd.DataFrame) -> set[str]:
        """Accounts at this institution with ≥1 cross-institution transaction."""
        cross = df[df["cross"]]
        # Accounts that send cross-institution
        senders = set(cross[cross["from_inst"] == self.bank_id]["from_acct"].astype(str))
        # Accounts that receive cross-institution
        receivers = set(cross[cross["to_inst"] == self.bank_id]["to_acct"].astype(str))
        return senders | receivers

    def prepare_cross_bank_txns(self, df: pd.DataFrame) -> list[CrossBankTxn]:
        """Extract cross-bank transactions involving this bank."""
        cross = df[df["cross"]].copy()
        txns: list[CrossBankTxn] = []

        # Outgoing: this bank is the sender
        outgoing = cross[cross["from_inst"] == self.bank_id]
        for _, row in outgoing.iterrows():
            txns.append(
                CrossBankTxn(
                    edge_ref=int(row["row_id"]),
                    own_account=str(row["from_acct"]),
                    direction="out",
                    counterparty_bank=int(row["to_bank"]),
                    counterparty_account=str(row["to_acct"]),
                    ts=int(row["ts"]),
                    amount=float(row["amt_paid"]),
                    currency=str(row["cur_paid"]),
                    fmt=str(row["fmt"]),
                )
            )

        # Incoming: this bank is the receiver
        incoming = cross[cross["to_inst"] == self.bank_id]
        for _, row in incoming.iterrows():
            txns.append(
                CrossBankTxn(
                    edge_ref=int(row["row_id"]),
                    own_account=str(row["to_acct"]),
                    direction="in",
                    counterparty_bank=int(row["from_bank"]),
                    counterparty_account=str(row["from_acct"]),
                    ts=int(row["ts"]),
                    amount=float(row["amt_recv"]),
                    currency=str(row["cur_recv"]),
                    fmt=str(row["fmt"]),
                )
            )

        return txns

    def prepare_boundary_summaries(
        self,
        boundary_accounts: set[str],
        local_features: pd.DataFrame,
    ) -> list[BoundarySummary]:
        """Build boundary summaries from locally computed features."""
        summaries: list[BoundarySummary] = []
        for acct in boundary_accounts:
            # Aggregate local features for this account (mean across its txns)
            acct_feats = (
                local_features[local_features.index.get_level_values("from_acct") == acct]
                if "from_acct" in local_features.index.names
                else pd.DataFrame()
            )

            from mritra.features.network import NETWORK_SUMMARY_DIM

            # Use zeros if no features available yet
            vec = [0.0] * NETWORK_SUMMARY_DIM if acct_feats.empty else acct_feats.mean().tolist()

            summaries.append(BoundarySummary(account=acct, features=vec))
        return summaries

    def create_submission(
        self,
        round_id: int,
        df: pd.DataFrame,
        local_features: pd.DataFrame | None = None,
    ) -> SealedEnvelope:
        """Build and encrypt a round submission."""
        boundary = self.identify_boundary_accounts(df)
        txns = self.prepare_cross_bank_txns(df)

        summaries = []
        if local_features is not None:
            summaries = self.prepare_boundary_summaries(boundary, local_features)

        submission = RoundSubmission(
            bank_id=self.bank_id,
            round_id=round_id,
            txns=txns,
            summaries=summaries,
        )

        return encrypt_submission(submission, self.private_key, self.enclave_public_key)

    def receive_features(self, features: list[NetworkFeatures]) -> pd.DataFrame:
        """Convert received network features to a DataFrame."""
        if not features:
            return pd.DataFrame()

        from mritra.features.network import NETWORK_SUMMARY_DIM, network_feature_names

        names = network_feature_names(NETWORK_SUMMARY_DIM)
        rows = []
        for f in features:
            row = {"account": f.account, "round_id": f.round_id}
            for name, v in zip(names, f.features, strict=True):
                row[name] = v
            rows.append(row)
        return pd.DataFrame(rows)

import os
import glob
import json
from pathlib import Path
from fastapi import FastAPI

app = FastAPI(title="Bank Service API")

BANK_ID_STR = os.getenv("BANK_ID", "B0")

@app.get("/v1/health")
def health():
    return {"status": "ok", "bank_id": BANK_ID_STR}

@app.get("/v1/cases")
def get_cases(limit: int = 10):
    runs_dir = Path("results/runs")
    cases = []
    if runs_dir.exists():
        runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
        if runs:
            latest_run = runs[-1]
            eval_file = latest_run / "eval.json"
            if eval_file.exists():
                with open(eval_file, "r") as f:
                    data = json.load(f)
                # Generate mock cases for the datathon demo based on the eval data existing
                for i in range(limit):
                    cases.append({
                        "account": f"{BANK_ID_STR}_acct_{i}",
                        "score": round(0.99 - (i * 0.01), 4),
                        "flagged": True
                    })
    
    if not cases:
        for i in range(limit):
            cases.append({
                "account": f"{BANK_ID_STR}_acct_{i}",
                "score": round(0.99 - (i * 0.01), 4),
                "flagged": True
            })
            
    return {"bank_id": BANK_ID_STR, "cases": cases}

@app.get("/v1/exposure/{round_id}")
def get_exposure(round_id: int):
    return {
        "round_id": round_id,
        "bank_id": BANK_ID_STR,
        "bytes_sent": 1024 * (round_id + 1),
        "fields_exposed": ["amount", "ts", "currency", "fmt", "own_account", "counterparty_bank", "counterparty_account"]
    }
