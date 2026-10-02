"""Replay transactions as a stream for the live demo (plan §5 / §16).

Replays one split, one simulated hour at a time, driving the bank services
and enclave through the boundary protocol. Defaults to the split named in
configs/experiment.yaml: demo.default_replay_split ("val"); the test split
can only be replayed with an explicit --split test --confirm-test-split,
since CLAUDE.md §8 says not to touch it during development.
"""

from __future__ import annotations

import argparse
import logging
import time

import pandas as pd

from mritra.config import load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.data.split import temporal_split
from mritra.protocol.crypto import KeyPair
from mritra.services.bank_service import BankService
from mritra.services.enclave_service import EnclaveService

logger = logging.getLogger("replay_stream")

HOUR_SEC = 3600


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay one split's transactions as a stream.")
    parser.add_argument("--speed", type=float, default=0.0, help="Delay between rounds (seconds)")
    parser.add_argument("--max-rounds", type=int, default=None, help="Limit number of rounds")
    parser.add_argument(
        "--split",
        choices=["train", "val", "test"],
        default=None,
        help="Split to replay. Defaults to configs/experiment.yaml: demo.default_replay_split.",
    )
    parser.add_argument(
        "--confirm-test-split",
        action="store_true",
        help="Required in addition to --split test; replaying the test split during "
        "development is against CLAUDE.md §8.",
    )
    args = parser.parse_args()

    cfg = load_config()
    k = cfg["institutions"]["k"]
    parquet = repo_path(cfg["paths"]["parquet"])
    results = repo_path(cfg["paths"]["results"])

    split = args.split or cfg["demo"]["default_replay_split"]
    if split == "test" and not args.confirm_test_split:
        parser.error("replaying the test split requires --split test --confirm-test-split")

    df = pd.read_parquet(parquet / "trans.parquet")
    inst_of = make_partition(df, cfg["partitions"]["P1"]["method"], k)
    df = add_institutions(df, inst_of)

    split_cfg = cfg["split"]
    df["split"] = temporal_split(df["ts"], split_cfg["train"], split_cfg["val"])
    replay_df = df[df["split"] == split].copy()

    if replay_df.empty:
        logger.error("No %s-split transactions found", split)
        return

    # Generate keys
    bank_keypairs = {i: KeyPair.generate() for i in range(k)}
    bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}

    tlog_path = results / "demo_tlog.db"
    enclave = EnclaveService(tlog_path, bank_public_keys)

    bank_services = {
        i: BankService(i, bank_keypairs[i].private_key, enclave.public_key) for i in range(k)
    }

    # Replay by hour
    ts_min = int(replay_df["ts"].min())
    ts_max = int(replay_df["ts"].max())
    round_id = 0

    for t_start in range(ts_min, ts_max + 1, HOUR_SEC):
        t_end = t_start + HOUR_SEC
        window = replay_df[(replay_df["ts"] >= t_start) & (replay_df["ts"] < t_end)]

        if window.empty:
            continue

        round_id += 1
        if args.max_rounds and round_id > args.max_rounds:
            break

        # Each bank creates and encrypts its submission
        envelopes = []
        for inst_id, bank in bank_services.items():
            inst_window = window[(window["from_inst"] == inst_id) | (window["to_inst"] == inst_id)]
            if inst_window.empty:
                continue
            envelope = bank.create_submission(round_id, inst_window)
            envelopes.append(envelope)

        # Enclave processes
        if envelopes:
            responses = enclave.process_round(round_id, envelopes, as_of=t_end)
            for bank_id, resp in responses.items():
                bank_services[bank_id].receive_features(resp.features)

        logger.info(
            "Round %d: t=[%d, %d) txns=%d envelopes=%d",
            round_id,
            t_start,
            t_end,
            len(window),
            len(envelopes),
        )

        if args.speed > 0:
            time.sleep(args.speed)

    enclave.close()
    logger.info("Replay complete: split=%s rounds=%d", split, round_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
