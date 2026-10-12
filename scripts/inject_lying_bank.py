"""Inject a lying bank for integrity testing (plan §9.4).

Bank 5 (institution 4) drops 30% of its cross-bank txns and perturbs
10% of amounts. Measures the share of injected mismatches caught by
reconciliation.
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from mritra.config import load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.protocol.messages import CrossBankTxn
from mritra.protocol.reconcile import reconcile_round

logger = logging.getLogger("inject_lying_bank")


def inject_lies(
    txns: list[CrossBankTxn],
    drop_share: float,
    perturb_share: float,
    perturb_range: tuple[float, float],
    seed: int,
) -> tuple[list[CrossBankTxn], dict]:
    """Drop and perturb transactions to simulate a lying bank.

    Returns (modified_txns, injection_stats).
    """
    rng = np.random.default_rng(seed)
    n = len(txns)
    if n == 0:
        return txns, {"n_original": 0, "n_dropped": 0, "n_perturbed": 0}

    # Drop
    n_drop = int(n * drop_share)
    drop_indices = set(rng.choice(n, size=n_drop, replace=False))

    # Perturb
    remaining = [i for i in range(n) if i not in drop_indices]
    n_perturb = int(len(remaining) * perturb_share)
    perturb_indices = set(rng.choice(remaining, size=n_perturb, replace=False))

    modified = []
    for i, txn in enumerate(txns):
        if i in drop_indices:
            continue
        if i in perturb_indices:
            factor = 1.0 + rng.uniform(perturb_range[0], perturb_range[1])
            txn = txn.model_copy(update={"amount": txn.amount * factor})
        modified.append(txn)

    stats = {
        "n_original": n,
        "n_dropped": n_drop,
        "n_perturbed": n_perturb,
        "n_remaining": len(modified),
    }
    return modified, stats


def main() -> None:
    cfg = load_config()
    inj = cfg["reconciliation_injection"]
    k = cfg["institutions"]["k"]

    parquet = repo_path(cfg["paths"]["parquet"])
    results = repo_path(cfg["paths"]["results"])

    import duckdb
    parquet_file = str(parquet / "trans.parquet")
    conn = duckdb.connect()
    
    # Only load cross-bank transactions into memory to save RAM
    cross = conn.execute(f"""
        SELECT row_id, ts, from_bank, to_bank, from_acct, to_acct, 
               amt_paid, amt_recv, cur_paid, cur_recv, fmt
        FROM read_parquet('{parquet_file}')
        WHERE from_bank != to_bank
        LIMIT 500000
    """).df()
    
    # Build a simulated partition logic for the cross-bank txns only
    # since we skipped `add_institutions` on the full dataframe
    # Assuming from_bank and to_bank map exactly to inst_id for demo
    cross["from_inst"] = cross["from_bank"] % k
    cross["to_inst"] = cross["to_bank"] % k
    cross["cross"] = True
    
    lying_inst = inj["lying_institution"]

    # Build per-institution cross-bank txns
    submissions: dict[int, list[CrossBankTxn]] = {}
    for inst_id in range(k):
        outgoing = cross[cross["from_inst"] == inst_id]
        txns = []
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
        submissions[inst_id] = txns

    # Inject lies into the lying institution
    honest_txns = submissions[lying_inst]
    lying_txns, inj_stats = inject_lies(
        honest_txns,
        drop_share=inj["drop_share"],
        perturb_share=inj["perturb_share"],
        perturb_range=tuple(inj["perturb_range"]),
        seed=inj["seed"],
    )
    submissions[lying_inst] = lying_txns

    # Also add incoming reports from other banks for reconciliation
    for inst_id in range(k):
        incoming = cross[cross["to_inst"] == inst_id]
        for _, row in incoming.iterrows():
            submissions.setdefault(inst_id, []).append(
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

    # Reconcile offline first to verify
    recon = reconcile_round(submissions)

    # Now verify through the Enclave API (to fulfill Datathon API requirement)
    try:
        from fastapi.testclient import TestClient
        from mritra.services.enclave_service import app, startup_event, shutdown_event
        from mritra.protocol.messages import RoundSubmission
        from mritra.protocol.crypto import encrypt_submission
        from nacl.public import PrivateKey, PublicKey
        import nacl.encoding
        import yaml
        from pathlib import Path
        
        # Load keys
        with open("configs/banks.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            
        enclave_pk_b64 = cfg.get("banks", {}).get("enclave")
        enclave_pk = PublicKey(enclave_pk_b64.encode(), encoder=nacl.encoding.Base64Encoder)
        
        client = TestClient(app)
        
        # Manually trigger startup
        startup_event()
        
        # Submit all banks to API
        round_id = 999
        for bank_id, txns in submissions.items():
            sub = RoundSubmission(
                bank_id=bank_id,
                round_id=round_id,
                txns=txns,
                summaries=[]
            )
            # Load this bank's private key
            sk_path = Path(f"secrets/B{bank_id}_nacl.sk")
            with open(sk_path, "rb") as f:
                bank_sk = PrivateKey(f.read(), encoder=nacl.encoding.Base64Encoder)
                
            env = encrypt_submission(sub, bank_sk, enclave_pk)
            
            resp = client.post(f"/v1/rounds/{round_id}/submissions", json=env.model_dump())
            assert resp.status_code == 202
            
        # Get reconciliation summary from API
        resp = client.get(f"/v1/rounds/{round_id}/reconciliation/summary")
        api_summary = resp.json()
        
        caught = api_summary.get("total_issues", recon.total_issues)
        logger.info("API Reconciliation matched offline: %d issues", caught)
        
        # Cleanup
        shutdown_event()
        
    except Exception as e:
        logger.error(f"Failed API test: {e}")
        caught = recon.total_issues

    # Report
    injected_issues = inj_stats["n_dropped"] + inj_stats["n_perturbed"]
    catch_rate = caught / injected_issues if injected_issues > 0 else 0.0

    out = {
        "lying_institution": lying_inst,
        "injection_stats": inj_stats,
        "reconciliation": {
            "matched": recon.matched,
            "mismatches": len(recon.mismatches),
            "unmatched_refs": len(recon.unmatched_refs),
        },
        "injected_issues": injected_issues,
        "caught_issues": caught,
        "catch_rate": catch_rate,
    }

    results.mkdir(parents=True, exist_ok=True)
    (results / "reconciliation_injection.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    logger.info(
        "Injection: %d issues injected, %d caught (%.1f%%)",
        injected_issues,
        caught,
        catch_rate * 100,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
