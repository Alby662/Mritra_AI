# ruff: noqa: E501
import tempfile
from pathlib import Path

import pandas as pd


def test_c3_build_prevents_same_round_and_future_leakage():
    from mritra.protocol.crypto import KeyPair
    from mritra.services.bank_service import BankService
    from mritra.services.enclave_service import EnclaveService

    t0 = 1000
    window_sec = 1000

    # Toy dataset:
    # Round 0:
    #   ts=1100 (t0+100) -> Acct A sends to Acct B.
    #   ts=1900 (t0+900) -> Acct A sends to Acct C.
    # Round 1:
    #   ts=2100 (t0+1100) -> Acct A sends to Acct D.

    df = pd.DataFrame(
        [
            {
                "row_id": 0,
                "ts": 1100,
                "from_inst": 0,
                "to_inst": 1,
                "from_acct": "0_A",
                "to_acct": "1_B",
                "amount": 100.0,
                "edge_ref": 0,
                "amt_paid": 100.0,
                "amt_recv": 100.0,
                "cross": True,
                "from_bank": 0,
                "to_bank": 1,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
            },
            {
                "row_id": 1,
                "ts": 1900,
                "from_inst": 0,
                "to_inst": 1,
                "from_acct": "0_A",
                "to_acct": "1_C",
                "amount": 200.0,
                "edge_ref": 1,
                "amt_paid": 200.0,
                "amt_recv": 200.0,
                "cross": True,
                "from_bank": 0,
                "to_bank": 1,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
            },
            {
                "row_id": 2,
                "ts": 2100,
                "from_inst": 0,
                "to_inst": 1,
                "from_acct": "0_A",
                "to_acct": "1_D",
                "amount": 300.0,
                "edge_ref": 2,
                "amt_paid": 300.0,
                "amt_recv": 300.0,
                "cross": True,
                "from_bank": 0,
                "to_bank": 1,
                "cur_paid": "USD",
                "cur_recv": "USD",
                "fmt": "ACH",
            },
        ]
    )

    df["round_id"] = (df["ts"] - t0) // window_sec

    k = 2
    with tempfile.TemporaryDirectory() as d:
        tlog_path = Path(d) / "tlog.db"
        bank_keypairs = {i: KeyPair.generate() for i in range(k)}
        bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}
        enclave = EnclaveService(tlog_path, bank_public_keys)
        banks = {
            i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)
        }

        accumulated_net_features = {i: [] for i in range(k)}
        rounds = sorted(df["round_id"].unique())

        for r_id in rounds:
            envelopes = []
            round_df = df[df["round_id"] == r_id]
            for bank_id in range(k):
                bank_df = round_df[
                    (round_df["from_inst"] == bank_id) | (round_df["to_inst"] == bank_id)
                ]
                env = banks[bank_id].create_submission(
                    int(r_id), bank_df, local_features=pd.DataFrame()
                )
                envelopes.append(env)

            as_of = t0 + (r_id + 1) * window_sec
            responses = enclave.process_round(int(r_id), envelopes, as_of=as_of)

            for bank_id, resp in responses.items():
                if resp.features:
                    accumulated_net_features[bank_id].extend(resp.features)

        bank_id = 0
        net_df = banks[bank_id].receive_features(accumulated_net_features[bank_id])

        combined = df[(df["from_inst"] == bank_id) | (df["to_inst"] == bank_id)].copy()

        combined["round_id"] = (combined["ts"] - t0) // window_sec
        net_df["target_round_id"] = net_df["round_id"] + 1
        net_df = net_df.sort_values("target_round_id")

        net_df_ffill = (
            net_df.drop(columns=["round_id"])
            .groupby(["account", "target_round_id"])
            .last()
            .reset_index()
        )

        combined = combined.merge(
            net_df_ffill,
            left_on=["from_acct", "round_id"],
            right_on=["account", "target_round_id"],
            how="left",
        )

        r0 = combined[combined["round_id"] == 0]
        assert r0["net_fan_out"].isna().all(), (
            "Round 0 transactions incorrectly saw same-round features!"
        )

        r1 = combined[combined["round_id"] == 1].iloc[0]
        assert not pd.isna(r1["net_fan_out"]), (
            "Round 1 transaction did not see historical features!"
        )
        assert r1["net_fan_out"] == 2.0, f"Expected fan_out=2, got {r1['net_fan_out']}"


# noqa: E501
