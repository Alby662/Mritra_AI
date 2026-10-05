import tempfile
from pathlib import Path

import numpy as np

from mritra.protocol.crypto import KeyPair, encrypt_submission
from mritra.protocol.messages import BoundarySummary, CrossBankTxn, RoundSubmission
from mritra.services.bank_service import BankService
from mritra.services.enclave_service import EnclaveService


def test_bank_cannot_poison_peer_summaries():
    with tempfile.TemporaryDirectory() as d:
        tlog_path = Path(d) / "tlog.db"

        bank0_kp = KeyPair.generate()
        bank1_kp = KeyPair.generate()
        bank_public_keys = {0: bank0_kp.public_key, 1: bank1_kp.public_key}
        enclave = EnclaveService(tlog_path, bank_public_keys)

        bank0 = BankService(0, bank0_kp.private_key, enclave.public_key)
        bank1 = BankService(1, bank1_kp.private_key, enclave.public_key)

        # Bank 1 submits a cross-bank transaction (Bank 1 -> Bank 0) and its legitimate summary
        legit_summary = BoundarySummary(account="B_Acc", features=[1.0] * 6)
        txn1 = CrossBankTxn(
            edge_ref=100,
            own_account="B_Acc",
            direction="out",
            counterparty_bank=0,
            counterparty_account="A_Acc",
            ts=10,
            amount=50.0,
            currency="USD",
            fmt="WIRE",
        )
        sub1 = RoundSubmission(bank_id=1, round_id=0, txns=[txn1], summaries=[legit_summary])
        env1 = encrypt_submission(sub1, bank1.private_key, bank1.enclave_public_key)

        # Bank 0 maliciously tries to poison Bank 1's account
        poison_summary = BoundarySummary(account="B_Acc", features=[99.0] * 6)
        legit_summary_0 = BoundarySummary(account="A_Acc", features=[2.0] * 6)
        txn0 = CrossBankTxn(
            edge_ref=100,
            own_account="A_Acc",
            direction="in",
            counterparty_bank=1,
            counterparty_account="B_Acc",
            ts=10,
            amount=50.0,
            currency="USD",
            fmt="WIRE",
        )
        sub0 = RoundSubmission(
            bank_id=0, round_id=0, txns=[txn0], summaries=[poison_summary, legit_summary_0]
        )
        env0 = encrypt_submission(sub0, bank0.private_key, bank0.enclave_public_key)

        # Process round
        responses = enclave.process_round(round_id=0, envelopes=[env0, env1], as_of=20)

        # Enclave physically segregates state using authenticated bank_id
        assert "1_B_Acc" in enclave._latest_summaries
        np.testing.assert_array_equal(enclave._latest_summaries["1_B_Acc"], np.array([1.0] * 6))
        assert "0_B_Acc" in enclave._latest_summaries
        np.testing.assert_array_equal(enclave._latest_summaries["0_B_Acc"], np.array([99.0] * 6))

        # Check Bank 1's final returned network features for B_Acc
        b1_resp = responses[1]
        b1_feats = {f.account: f.features for f in b1_resp.features}
        assert "B_Acc" in b1_feats

        expected_struct = [1.0, 0.0, 50.0, 0.0, 0.0]
        expected_agg = [2.0] * 6 + [2.0] * 6 + [2.0] * 6
        expected_total = expected_struct + expected_agg

        np.testing.assert_array_almost_equal(b1_feats["B_Acc"], expected_total)
        print("Poisoning attempt completely failed to affect final computed features.")
