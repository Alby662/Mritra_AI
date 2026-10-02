"""No-future-leakage tests for feature code (CLAUDE.md §6: "feature at t unchanged when
later rows are appended").

Covers behaviour.py, graph_gfp.py (round-windowed streaming, see its module docstring for
why and how) and network.py (explicit ``as_of`` cutoff, enforced by the function itself).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mritra.features.behaviour import compute_behavioural_features
from mritra.features.graph_gfp import compute_gfp_features, load_gfp_config
from mritra.features.network import compute_network_features
from mritra.protocol.rounds import round_id_for_ts


def _toy_transactions(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    insts = [0, 1]
    accts = ["A", "B", "C"]
    rows = []
    for i in range(n):
        fi, ti = rng.choice(insts, size=2, replace=False)
        fa, ta = rng.choice(accts, size=2, replace=False)
        rows.append(
            {
                "row_id": i,
                "ts": 1_000 + i * 100,
                "from_inst": fi,
                "from_acct": fa,
                "to_inst": ti,
                "to_acct": ta,
                "amt_paid": 100.0 + i,
                "amt_recv": 95.0 + i,
                "fmt": rng.choice(["ACH", "Wire"]),
                "cur_paid": "USD",
            }
        )
    return pd.DataFrame(rows)


def test_behavioural_features_unchanged_when_future_rows_appended() -> None:
    df = _toy_transactions(n=25, seed=1)
    cutoff = 15

    before = compute_behavioural_features(df.iloc[:cutoff].copy())
    after = compute_behavioural_features(df.copy())  # 10 more rows, all ts > cutoff's rows

    shared_ids = before.index
    pd.testing.assert_frame_equal(
        before.loc[shared_ids].sort_index(),
        after.loc[shared_ids].sort_index(),
        check_like=False,
    )


def _toy_boundary_edges(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    accounts = ["a1", "a2", "a3", "a4"]
    rows = []
    for i in range(n):
        f, t = rng.choice(accounts, size=2, replace=False)
        rows.append(
            {"edge_ref": i, "from_acct": f, "to_acct": t, "ts": 1_000 + i * 10, "amount": 50.0 + i}
        )
    return pd.DataFrame(rows)


def test_network_features_raise_on_edge_at_or_after_as_of() -> None:
    edges = _toy_boundary_edges(n=5, seed=2)
    as_of = int(edges["ts"].max())  # the last edge has ts == as_of, not < as_of
    with pytest.raises(ValueError, match="as_of"):
        compute_network_features(edges, {}, as_of=as_of)


def test_enclave_two_round_toy_run_round1_unaffected_by_round2() -> None:
    """Integration: BankService + EnclaveService over two rounds. Round 1's returned
    features must not change whether or not round 2 ever happens."""
    from mritra.protocol.crypto import KeyPair
    from mritra.services.bank_service import BankService
    from mritra.services.enclave_service import EnclaveService

    k = 2
    bank_keypairs = {i: KeyPair.generate() for i in range(k)}
    bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}

    def make_enclave(tlog_path: Path) -> EnclaveService:
        return EnclaveService(tlog_path, bank_public_keys)

    def make_banks(enclave: EnclaveService) -> dict[int, BankService]:
        return {
            i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)
        }

    # Round 1: one cross-bank txn 0 -> 1. Round 2 (later ts): another, different accounts.
    round1_df = pd.DataFrame(
        [
            {
                "row_id": 0,
                "from_bank": 0,
                "from_acct": "x1",
                "to_bank": 1,
                "to_acct": "y1",
                "ts": 1_000,
                "amt_paid": 100.0,
                "amt_recv": 100.0,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
                "from_inst": 0,
                "to_inst": 1,
                "cross": True,
            }
        ]
    )
    round2_df = pd.DataFrame(
        [
            {
                "row_id": 1,
                "from_bank": 0,
                "from_acct": "x1",
                "to_bank": 1,
                "to_acct": "y2",
                "ts": 5_000,
                "amt_paid": 999.0,
                "amt_recv": 999.0,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
                "from_inst": 0,
                "to_inst": 1,
                "cross": True,
            }
        ]
    )

    def run_round1_only(tlog_path: Path) -> dict:
        enclave = make_enclave(tlog_path)
        banks = make_banks(enclave)
        envelopes = [b.create_submission(1, round1_df) for b in banks.values()]
        responses = enclave.process_round(1, envelopes, as_of=2_000)
        enclave.close()
        return {bid: [f.features for f in r.features] for bid, r in responses.items()}

    def run_round1_then_round2(tlog_path: Path) -> dict:
        enclave = make_enclave(tlog_path)
        banks = make_banks(enclave)
        envelopes1 = [b.create_submission(1, round1_df) for b in banks.values()]
        round1_responses = {
            bid: [f.features for f in r.features]
            for bid, r in enclave.process_round(1, envelopes1, as_of=2_000).items()
        }
        envelopes2 = [b.create_submission(2, round2_df) for b in banks.values()]
        enclave.process_round(2, envelopes2, as_of=6_000)
        enclave.close()
        return round1_responses

    import tempfile

    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        only1 = run_round1_only(Path(d1) / "t.db")
        with_round2 = run_round1_then_round2(Path(d2) / "t.db")

    assert only1 == with_round2


def _two_round_persistence_scenario() -> tuple:
    """Same cross-bank pair (bank0's x1 -> bank1's y1) sends once in round 1 and again in
    round 2, so a correctly persistent enclave's round-2 features for y1 should reflect
    BOTH edges (fan-in 2), not just round 2's single edge (fan-in 1)."""
    from mritra.protocol.crypto import KeyPair
    from mritra.services.bank_service import BankService
    from mritra.services.enclave_service import EnclaveService

    k = 2
    bank_keypairs = {i: KeyPair.generate() for i in range(k)}
    bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}

    def txn_row(row_id: int, ts: int) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "row_id": row_id,
                    "from_bank": 0,
                    "from_acct": "x1",
                    "to_bank": 1,
                    "to_acct": "y1",
                    "ts": ts,
                    "amt_paid": 100.0 + row_id,
                    "amt_recv": 100.0 + row_id,
                    "cur_paid": "USD",
                    "cur_recv": "USD",
                    "fmt": "ACH",
                    "from_inst": 0,
                    "to_inst": 1,
                    "cross": True,
                }
            ]
        )

    round1_df = txn_row(0, 1_000)
    round2_df = txn_row(1, 5_000)
    return k, bank_keypairs, bank_public_keys, round1_df, round2_df, EnclaveService, BankService


def test_enclave_round2_features_reflect_round1_edges(tmp_path: Path) -> None:
    (
        k,
        bank_keypairs,
        bank_public_keys,
        round1_df,
        round2_df,
        EnclaveService,
        BankService,
    ) = _two_round_persistence_scenario()

    enclave = EnclaveService(tmp_path / "t.db", bank_public_keys)
    banks = {i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)}

    envelopes1 = [b.create_submission(1, round1_df) for b in banks.values()]
    enclave.process_round(1, envelopes1, as_of=2_000)

    envelopes2 = [b.create_submission(2, round2_df) for b in banks.values()]
    responses2 = enclave.process_round(2, envelopes2, as_of=6_000)
    enclave.close()

    # Bank 1's account y1: feature index 1 is fan-in (mritra/features/network.py).
    # Two cumulative edges (round 1 + round 2) -> fan-in must be 2, not 1.
    y1_features = next(f for f in responses2[1].features if f.account == "y1")
    assert y1_features.features[1] == 2.0


def test_enclave_accumulated_state_equals_one_shot_batch_build(tmp_path: Path) -> None:
    from mritra.features.network import compute_network_features

    (
        k,
        bank_keypairs,
        bank_public_keys,
        round1_df,
        round2_df,
        EnclaveService,
        BankService,
    ) = _two_round_persistence_scenario()

    enclave = EnclaveService(tmp_path / "t.db", bank_public_keys)
    banks = {i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)}

    envelopes1 = [b.create_submission(1, round1_df) for b in banks.values()]
    enclave.process_round(1, envelopes1, as_of=2_000)
    envelopes2 = [b.create_submission(2, round2_df) for b in banks.values()]
    responses2 = enclave.process_round(2, envelopes2, as_of=6_000)
    enclave.close()

    # One-shot: build the same two edges directly and call compute_network_features once,
    # bypassing the enclave's round-by-round accumulation entirely.
    one_shot_edges = pd.DataFrame(
        [
            {"edge_ref": 0, "from_acct": "0_x1", "to_acct": "1_y1", "ts": 1_000, "amount": 100.0},
            {"edge_ref": 1, "from_acct": "0_x1", "to_acct": "1_y1", "ts": 5_000, "amount": 101.0},
        ]
    )
    one_shot = compute_network_features(one_shot_edges, {}, as_of=6_000)

    y1_from_rounds = next(f for f in responses2[1].features if f.account == "y1")
    np.testing.assert_array_equal(np.array(y1_from_rounds.features), one_shot["1_y1"])


def _toy_graph_edges(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    accounts = ["A", "B", "C", "D", "E"]
    rows = []
    for i in range(n):
        f, t = rng.choice(accounts, size=2, replace=False)
        rows.append(
            {
                "row_id": i,
                "from_bank": 0,
                "from_acct": f,
                "to_bank": 1,
                "to_acct": t,
                "ts": 1_000 + i * 300,  # 5 min apart -> several round-window batches
                "amt_paid": 100.0 + i,
            }
        )
    return pd.DataFrame(rows)


def test_graph_gfp_features_unchanged_for_earlier_batches_real_snapml() -> None:
    pytest.importorskip("snapml")
    df = _toy_graph_edges(n=60, seed=0)
    round_window_sec = 3600
    t0 = 0

    # Cut at a round-window BOUNDARY, not an arbitrary row count: transform() computes a
    # batch's features from the graph *after* that whole batch is inserted (snapml
    # docstring), so edges within the same batch legitimately see each other. Truncating
    # mid-batch would make the last partial batch differ for a reason that has nothing to
    # do with future leakage -- see the session report for the exploratory version of this
    # test that did that and was misleading.
    batch_id = round_id_for_ts(df["ts"].to_numpy(), t0, round_window_sec)
    b_cut = batch_id[40]
    earlier_batches = df[batch_id <= b_cut].copy()

    cfg = load_gfp_config()
    before = compute_gfp_features(earlier_batches, t0, cfg, round_window_sec=round_window_sec)
    after = compute_gfp_features(df.copy(), t0, cfg, round_window_sec=round_window_sec)

    shared_ids = before.index
    pd.testing.assert_frame_equal(
        before.loc[shared_ids].sort_index(),
        after.loc[shared_ids].sort_index(),
        check_like=False,
    )
