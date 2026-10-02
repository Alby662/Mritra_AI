"""Only reconciled-matched transactions enter the persistent boundary graph
(PROTOCOL.md §6 step 3).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from mritra.protocol.crypto import KeyPair
from mritra.services.bank_service import BankService
from mritra.services.enclave_service import EnclaveService


def _make_enclave_and_banks(tmp_path: Path, k: int = 2):
    bank_keypairs = {i: KeyPair.generate() for i in range(k)}
    bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}
    enclave = EnclaveService(tmp_path / "t.db", bank_public_keys)
    banks = {i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)}
    return enclave, banks


def _cross_bank_txn(
    row_id: int, from_acct: str, to_acct: str, ts: int, amount: float
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "row_id": row_id,
                "from_bank": 0,
                "from_acct": from_acct,
                "to_bank": 1,
                "to_acct": to_acct,
                "ts": ts,
                "amt_paid": amount,
                "amt_recv": amount,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
                "from_inst": 0,
                "to_inst": 1,
                "cross": True,
            }
        ]
    )


def test_one_sided_unmatched_edge_does_not_enter_boundary_graph(tmp_path: Path) -> None:
    """A bank reports a cross-bank txn but the counterparty bank never submits a matching
    report this round (a one-sided / "lying bank dropped it" case) -- unmatched, so it
    must never reach compute_network_features, and the reporting account must get no
    network features at all (not even zeros) since it has no matched edges."""
    enclave, banks = _make_enclave_and_banks(tmp_path)
    round_df = _cross_bank_txn(0, "x1", "y1", ts=1_000, amount=500.0)

    # Only bank 0 submits; bank 1 never reports its side -> edge_ref 0 is unmatched.
    envelope = banks[0].create_submission(1, round_df)
    responses = enclave.process_round(1, [envelope], as_of=2_000)
    enclave.close()

    assert enclave.boundary_edge_count == 0
    # x1 "appeared" (bank 0 reported it) but has no matched edge, so no features at all.
    assert all(f.account != "x1" for f in responses[0].features)


def test_matched_edge_does_enter_boundary_graph(tmp_path: Path) -> None:
    """Sanity check / contrast: the same transaction, reported by BOTH sides, is matched
    and does enter the graph -- isolates that the previous test's absence is specifically
    about matching, not some other regression."""
    enclave, banks = _make_enclave_and_banks(tmp_path)
    round_df = _cross_bank_txn(0, "x1", "y1", ts=1_000, amount=500.0)

    envelopes = [b.create_submission(1, round_df) for b in banks.values()]
    responses = enclave.process_round(1, envelopes, as_of=2_000)
    enclave.close()

    assert enclave.boundary_edge_count == 1
    x1_feat = next(f for f in responses[0].features if f.account == "x1")
    assert x1_feat.features[0] == 1.0  # net_fan_out


def test_mismatched_amount_edge_does_not_enter_boundary_graph(tmp_path: Path) -> None:
    """Both sides report the same edge_ref, but with different amounts -- a field
    mismatch, not a match (PROTOCOL.md §6 step 3's exact-field-agreement rule) -- so it
    must not enter the graph either, same as an unmatched one-sided report."""
    enclave, banks = _make_enclave_and_banks(tmp_path)

    sender_df = _cross_bank_txn(0, "x1", "y1", ts=1_000, amount=500.0)
    receiver_df = _cross_bank_txn(0, "x1", "y1", ts=1_000, amount=999.0)  # lying about amount

    env0 = banks[0].create_submission(1, sender_df)
    env1 = banks[1].create_submission(1, receiver_df)
    responses = enclave.process_round(1, [env0, env1], as_of=2_000)
    enclave.close()

    assert enclave.boundary_edge_count == 0
    assert all(f.account != "x1" for f in responses[0].features)
    assert all(f.account != "y1" for f in responses[1].features)
