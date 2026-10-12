# ruff: noqa: E501
"""Build per-config, per-institution feature tables (PREREGISTRATION §5).

Uses mritra/features/views.py as the single source of truth for which edges each
configuration sees, then computes GFP + behavioural features on that edge scope (and
network features, for C3, per-institution -- see note below). Writes
results/runs/<run_id>/features/<config>/<scope>.parquet and a run manifest.

Batched Execution: Iteratively loads data in chunks, strictly preserving the
3600-second round boundaries, to avoid OOM crashes on large datasets.
"""

from __future__ import annotations

import argparse
import logging
import tempfile
import os
import gc
import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from mritra.config import config_sha256, load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.features.behaviour import compute_behavioural_features
from mritra.features.graph_gfp import GFPStreamer, load_gfp_config
from mritra.features.views import feature_view
from mritra.protocol.crypto import KeyPair
from mritra.protocol.rounds import round_id_for_ts, round_window_sec
from mritra.runs import new_run_id, run_dir, snapml_version, write_manifest
from mritra.services.bank_service import BankService
from mritra.services.enclave_service import EnclaveService

logger = logging.getLogger("build_features")

def _should_skip(out_path: Path, expected_cols: list[str]) -> bool:
    if not out_path.exists():
        return False
    out_mtime = out_path.stat().st_mtime
    deps = [
        "scripts/build_features.py",
        "mritra/features/network.py",
        "mritra/features/views.py",
        "mritra/features/graph_gfp.py",
        "mritra/features/behaviour.py",
    ]
    for dep in deps:
        if os.path.exists(dep) and os.stat(dep).st_mtime > out_mtime:
            return False

    schema = pq.read_schema(out_path)
    if not set(expected_cols).issubset(set(schema.names)):
        return False

    return True


def stream_transactions(parquet_path: Path, wanted_splits: set[str], inst_of: dict[int, int], t0: int, window_sec: int, chunk_size: int = 500_000, peak_ts_range: tuple[int, int] | None = None):
    """Yield transactions in chronologically sound batches.
    
    Ensures that each yielded chunk is bounded by complete 3600-second rounds.
    The final incomplete round in a batch is buffered and appended to the next batch.
    """
    import resource
    
    import pyarrow.compute as pc
    
    parquet_file = pq.ParquetFile(parquet_path)
    buffer = pd.DataFrame()
    for batch in parquet_file.iter_batches(batch_size=chunk_size):
        if peak_ts_range:
            mask = pc.and_kleene(
                pc.greater_equal(batch["ts"], peak_ts_range[0]),
                pc.less(batch["ts"], peak_ts_range[1])
            )
            batch = batch.filter(mask)
            
        if len(batch) == 0:
            continue
            
        chunk = batch.to_pandas()
        chunk = chunk[chunk["split"].isin(wanted_splits)].copy()
        if chunk.empty:
            continue
            
        chunk = add_institutions(chunk, inst_of)
        chunk["round_id"] = round_id_for_ts(chunk["ts"], t0, window_sec)
        
        combined = pd.concat([buffer, chunk], ignore_index=True)
        # Sort locally to preserve strict chronological causality for the rounds
        combined = combined.sort_values("ts", kind="stable").reset_index(drop=True)
        
        max_round = combined["round_id"].max()
        ready_mask = combined["round_id"] < max_round
        
        ready_df = combined[ready_mask]
        buffer = combined[~ready_mask].copy()
        
        if not ready_df.empty:
            yield ready_df
            
        del chunk, combined, ready_mask, ready_df
        gc.collect()
        
        # Telemetry: Check Max RSS
        max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        max_rss_gb = max_rss_kb / (1024 * 1024)
        if max_rss_gb > 11.0:
            logger.critical("Abnormal C++ Memory Spike Detected! Max RSS: %.2f GB", max_rss_gb)
        else:
            logger.info("Memory Telemetry: Max RSS %.2f GB", max_rss_gb)
            
    if not buffer.empty:
        yield buffer


def build_config_features(
    config: str,
    parquet_path: Path,
    wanted_splits: set[str],
    inst_of: dict[int, int],
    t0: int,
    k: int,
    feature_dir: Path,
    gfp_cfg: dict,
    window_sec: int,
    peak_ts_range: tuple[int, int] | None = None,
) -> dict[str, list[str]]:
    feature_columns: dict[str, list[str]] = {}

    if config == "C1":
        for bank_id in range(k):
            out_path = feature_dir / config / f"bank_{bank_id}.parquet"
            # Extract expected columns via a dummy DataFrame to satisfy feature_view schema
            dummy_df = pd.DataFrame(columns=["row_id", "ts", "from_bank", "from_acct", "to_bank", "to_acct", "amt_paid", "from_inst", "to_inst", "cross", "split"])
            view = feature_view("C1", dummy_df, bank_id=bank_id)
            expected_cols = view.feature_columns
            
            if _should_skip(out_path, expected_cols):
                feature_columns[str(bank_id)] = pq.read_schema(out_path).names
                logger.info("Skipping %s bank %d: already exists and is fresh", config, bank_id)
                continue

            logger.info("Computing %s bank %d features (streaming)...", config, bank_id)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = out_path.with_suffix(".tmp.parquet")
            
            gfp_streamer = GFPStreamer(t0, window_sec, gfp_cfg)
            writer = None
            rows_processed = 0
            
            for chunk in stream_transactions(parquet_path, wanted_splits, inst_of, t0, window_sec, peak_ts_range=peak_ts_range):
                chunk_view = feature_view("C1", chunk, bank_id=bank_id)
                edges = chunk_view.edges
                if edges.empty:
                    continue
                    
                gfp_feats = gfp_streamer.process_chunk(edges)
                behav_feats = compute_behavioural_features(edges)
                
                if gfp_feats.empty:
                    chunk_merged = behav_feats
                else:
                    chunk_merged = gfp_feats.join(behav_feats, how="outer")
                
                for col in chunk_merged.columns:
                    if chunk_merged[col].dtype == "float64":
                        chunk_merged[col] = chunk_merged[col].astype("float32")
                        
                table = pa.Table.from_pandas(chunk_merged)
                if writer is None:
                    writer = pq.ParquetWriter(tmp_path, table.schema)
                writer.write_table(table)
                rows_processed += len(chunk_merged)
                
                del edges, chunk_view, gfp_feats, behav_feats, chunk_merged, table
                gc.collect()
                
            if writer is not None:
                writer.close()
                tmp_path.rename(out_path)
                feature_columns[str(bank_id)] = expected_cols
                logger.info("%s bank %d: %d rows -> %s", config, bank_id, rows_processed, out_path)
            else:
                logger.warning("%s bank %d produced no rows", config, bank_id)

    elif config == "C3":
        ckpt_path = feature_dir / "C3" / "c3_enclave_checkpoint.pkl"
        bank_keypairs = {i: KeyPair.generate() for i in range(k)}
        banks = {
            i: BankService(i, bank_keypairs[i].private_key, bank_keypairs[i].public_key)
            for i in range(k)
        }
        if ckpt_path.exists():
            logger.info("Found C3 enclave checkpoint at %s, loading...", ckpt_path)
            with open(ckpt_path, "rb") as f:
                accumulated_net_features = pickle.load(f)
        else:
            with tempfile.TemporaryDirectory() as d:
                tlog_path = Path(d) / "tlog.db"
                bank_public_keys = {i: kp.public_key for i, kp in bank_keypairs.items()}
                enclave = EnclaveService(tlog_path, bank_public_keys)
                banks = {
                    i: BankService(i, bank_keypairs[i].private_key, enclave.public_key)
                    for i in range(k)
                }

                accumulated_net_features = {i: [] for i in range(k)}
                logger.info("Computing C3 enclave features (streaming)...")
                
                for chunk in stream_transactions(parquet_path, wanted_splits, inst_of, t0, window_sec, peak_ts_range=peak_ts_range):
                    rounds = sorted(chunk["round_id"].unique())
                    for r_id in rounds:
                        round_df = chunk[chunk["round_id"] == r_id]
                        envelopes = []
                        for bank_id in range(k):
                            bank_df = round_df[(round_df["from_inst"] == bank_id) | (round_df["to_inst"] == bank_id)]
                            env = banks[bank_id].create_submission(int(r_id), bank_df, local_features=pd.DataFrame())
                            envelopes.append(env)
                        
                        as_of = t0 + (r_id + 1) * window_sec
                        responses = enclave.process_round(int(r_id), envelopes, as_of=as_of)
                        
                        for bank_id, resp in responses.items():
                            if resp.features:
                                accumulated_net_features[bank_id].extend(resp.features)
                    del chunk
                    gc.collect()

                enclave.close()
                ckpt_path.parent.mkdir(parents=True, exist_ok=True)
                with open(ckpt_path, "wb") as f:
                    pickle.dump(accumulated_net_features, f)

        logger.info("Loading lightweight df_meta for C3 alignment...")
        table_c3 = pq.read_table(parquet_path, columns=["row_id", "ts", "from_acct"])
        df_meta = table_c3.to_pandas(categories=["from_acct"])
        df_meta = df_meta.set_index("row_id")

        from mritra.features.network import NETWORK_SUMMARY_DIM
        for bank_id in range(k):
            out_path = feature_dir / config / f"bank_{bank_id}.parquet"
            dummy_df = pd.DataFrame(columns=["row_id", "ts", "from_bank", "from_acct", "to_bank", "to_acct", "amt_paid", "from_inst", "to_inst", "cross", "split"])
            view = feature_view("C3", dummy_df, bank_id=bank_id, network_summary_dim=NETWORK_SUMMARY_DIM)
            expected_cols = view.feature_columns
            
            if _should_skip(out_path, expected_cols):
                feature_columns[str(bank_id)] = pq.read_schema(out_path).names
                logger.info("Skipping C3 bank %d: already exists and is fresh", bank_id)
                accumulated_net_features[bank_id] = []
                continue

            net_df = banks[bank_id].receive_features(accumulated_net_features[bank_id])
            accumulated_net_features[bank_id] = []  # Free RAM
            
            if not net_df.empty:
                net_df["target_round_id"] = net_df["round_id"] + 1
                net_df = (
                    net_df.drop(columns=["round_id"])
                    .groupby(["account", "target_round_id"])
                    .last()
                    .reset_index()
                )
                net_df = net_df.sort_values("target_round_id")
                net_df["account"] = net_df["account"].astype(str)

            c1_path = feature_dir / "C1" / f"bank_{bank_id}.parquet"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = out_path.with_suffix(".tmp.parquet")
            
            writer = None
            rows_processed = 0
            
            logger.info("Aligning and streaming C3 features for bank %d...", bank_id)
            c1_file = pq.ParquetFile(c1_path)
            for batch in c1_file.iter_batches(batch_size=500_000):
                c1_chunk = batch.to_pandas()
                if "row_id" not in c1_chunk.columns and c1_chunk.index.name == "row_id":
                    c1_chunk["row_id"] = c1_chunk.index
                elif "row_id" in c1_chunk.columns:
                    c1_chunk = c1_chunk.set_index("row_id", drop=False)
                
                if not net_df.empty:
                    r_ids = c1_chunk["row_id"].to_numpy()
                    merge_light = pd.DataFrame({
                        "row_id": r_ids,
                        "ts": df_meta.loc[r_ids, "ts"].values,
                        "from_acct": df_meta.loc[r_ids, "from_acct"].astype(str).values,
                    })
                    merge_light["round_id"] = round_id_for_ts(merge_light["ts"], t0, window_sec)
                    
                    # Stable secondary sort to guarantee deterministic alignment
                    merge_light = merge_light.sort_values(["ts", "row_id"], kind="stable")
                    
                    # Ensure monotonic sorting required by merge_asof
                    if not merge_light["round_id"].is_monotonic_increasing:
                        logger.warning("merge_light['round_id'] is not monotonic strictly, applying sort on round_id")
                        merge_light = merge_light.sort_values("round_id", kind="stable")
                    assert merge_light["round_id"].is_monotonic_increasing, "merge_light must be monotonically sorted by round_id for merge_asof"
                    
                    merged_light = pd.merge_asof(
                        merge_light, net_df, left_on="round_id", right_on="target_round_id", left_by="from_acct", right_by="account", direction="backward"
                    )
                    merged_light = merged_light.set_index("row_id").drop(
                        columns=["ts", "from_acct", "round_id", "target_round_id", "account"], errors="ignore"
                    )
                    
                    for col in merged_light.columns:
                        c1_chunk[col] = merged_light[col]

                # Ensure all network columns exist (fill NaN with 0 for zeros-padding)
                for col in expected_cols:
                    if col not in c1_chunk.columns:
                        c1_chunk[col] = 0.0

                c1_chunk = c1_chunk[expected_cols]

                table = pa.Table.from_pandas(c1_chunk)
                if writer is None:
                    writer = pq.ParquetWriter(tmp_path, table.schema)
                writer.write_table(table)
                rows_processed += len(c1_chunk)
                
                del c1_chunk, table
                if not net_df.empty:
                    del merge_light, merged_light
                gc.collect()

            if writer is not None:
                writer.close()
                tmp_path.rename(out_path)
                feature_columns[str(bank_id)] = expected_cols
                logger.info("C3 bank %d: %d rows -> %s", bank_id, rows_processed, out_path)
            
        del df_meta
        gc.collect()

    elif config == "C4":
        out_path = feature_dir / "C4" / "all.parquet"
        dummy_df = pd.DataFrame(columns=["row_id", "ts", "from_bank", "from_acct", "to_bank", "to_acct", "amt_paid", "from_inst", "to_inst", "cross", "split"])
        view = feature_view("C4", dummy_df)
        expected_cols = view.feature_columns
        
        if _should_skip(out_path, expected_cols):
            feature_columns["all"] = pq.read_schema(out_path).names
            logger.info("Skipping C4: already exists and is fresh")
            return feature_columns

        logger.info("Computing C4 features (streaming)...")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_suffix(".tmp.parquet")
        
        gfp_streamer = GFPStreamer(t0, window_sec, gfp_cfg)
        writer = None
        rows_processed = 0

        for chunk in stream_transactions(parquet_path, wanted_splits, inst_of, t0, window_sec, peak_ts_range=peak_ts_range):
            chunk_view = feature_view("C4", chunk)
            edges = chunk_view.edges
            if edges.empty:
                continue

            gfp_feats = gfp_streamer.process_chunk(edges)
            behav_feats = compute_behavioural_features(edges)

            if gfp_feats.empty:
                chunk_merged = behav_feats
            else:
                chunk_merged = gfp_feats.join(behav_feats, how="outer")

            for col in chunk_merged.columns:
                if chunk_merged[col].dtype == "float64":
                    chunk_merged[col] = chunk_merged[col].astype("float32")

            table = pa.Table.from_pandas(chunk_merged)
            if writer is None:
                writer = pq.ParquetWriter(tmp_path, table.schema)
            writer.write_table(table)
            rows_processed += len(chunk_merged)

            del edges, chunk_view, gfp_feats, behav_feats, chunk_merged, table
            gc.collect()

        if writer is not None:
            writer.close()
            tmp_path.rename(out_path)
            feature_columns["all"] = expected_cols
            logger.info("C4: %d rows -> %s", rows_processed, out_path)
        else:
            logger.warning("C4 produced no rows")

    return feature_columns


def main() -> None:
    parser = argparse.ArgumentParser(description="Build C1/C3/C4 feature tables.")
    parser.add_argument("--partition", choices=["P1", "P2"], default="P1")
    parser.add_argument("--configs", default="C1,C3,C4")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run-peak", action="store_true", help="Process only the densest 24-hour window for memory stress-testing.")
    parser.add_argument(
        "--splits",
        default="train,val,test",
        help="Comma-separated splits to include in the input data. Default includes test; "
        "pass --splits train,val to build features only (CLAUDE.md §8: don't touch the "
        "test split during development).",
    )
    args = parser.parse_args()

    cfg = load_config()
    k = cfg["institutions"]["k"]
    parquet = repo_path(cfg["paths"]["parquet"])
    parquet_path = parquet / "trans.parquet"

    wanted_splits = set(args.splits.split(","))
    
    # Lightweight metadata load to derive t0 and partitions
    logger.info("Computing t0, partition mapping, and peak day via pyarrow batches...")
    import pyarrow.compute as pc
    
    pf = pq.ParquetFile(parquet_path)
    t0_val = float('inf')
    from_counts_dict = {}
    to_counts_dict = {}
    
    for batch in pf.iter_batches(columns=["ts", "split", "from_bank", "to_bank"], batch_size=10_000_000):
        # Filter to wanted splits
        mask = pc.is_in(batch["split"], value_set=pa.array(list(wanted_splits)))
        batch = batch.filter(mask)
        if len(batch) == 0: continue
        
        # t0
        train_mask = pc.equal(batch["split"], "train")
        train_ts = batch["ts"].filter(train_mask)
        if len(train_ts) > 0:
            b_min = pc.min(train_ts).as_py()
            if b_min < t0_val: t0_val = b_min
            
        # from_bank
        fb_counts = pc.value_counts(batch["from_bank"])
        for val, count in zip(fb_counts.field("values"), fb_counts.field("counts")):
            from_counts_dict[val.as_py()] = from_counts_dict.get(val.as_py(), 0) + count.as_py()
            
        # to_bank
        tb_counts = pc.value_counts(batch["to_bank"])
        for val, count in zip(tb_counts.field("values"), tb_counts.field("counts")):
            to_counts_dict[val.as_py()] = to_counts_dict.get(val.as_py(), 0) + count.as_py()
            
    t0 = int(t0_val)
    
    # volumes
    fdf = pd.Series(from_counts_dict)
    tdf = pd.Series(to_counts_dict)
    volumes = fdf.add(tdf, fill_value=0).astype(int)
    
    part_cfg = cfg["partitions"][args.partition]
    if part_cfg["method"] == "volume_balanced":
        from mritra.data.partition import partition_volume_balanced
        inst_of = partition_volume_balanced(volumes, k)
    elif part_cfg["method"] == "random":
        from mritra.data.partition import partition_random
        inst_of = partition_random(list(volumes.index), k, part_cfg.get("seed", 42))
    else:
        inst_of = make_partition(pd.DataFrame(), part_cfg["method"], k) # dummy
    
    peak_ts_range = None
    if args.dry_run_peak:
        logger.info("Calculating densest 24-hour window for --dry-run-peak via batches...")
        day_counts = {}
        for batch in pf.iter_batches(columns=["ts", "split"], batch_size=10_000_000):
            mask = pc.is_in(batch["split"], value_set=pa.array(list(wanted_splits)))
            batch_ts = batch["ts"].filter(mask)
            if len(batch_ts) == 0: continue
            days = pc.cast(pc.divide(pc.subtract(batch_ts, t0), 86400), pa.int64())
            dc = pc.value_counts(days)
            for val, count in zip(dc.field("values"), dc.field("counts")):
                day_counts[val.as_py()] = day_counts.get(val.as_py(), 0) + count.as_py()
        
        peak_day = max(day_counts.items(), key=lambda x: x[1])[0]
        peak_start = int(t0 + peak_day * 86400)
        peak_ts_range = (peak_start, peak_start + 86400)
        logger.info(f"Dry-run peak mode enabled: Target window {peak_ts_range} (day {peak_day}, txns {day_counts[peak_day]})")
    

    gfp_cfg = load_gfp_config()
    window_sec = round_window_sec()

    run_id = args.run_id or new_run_id()
    feature_dir = run_dir(run_id) / "features"

    feature_columns_per_config = {}
    for config in args.configs.split(","):
        feature_columns_per_config[config] = build_config_features(
            config, parquet_path, wanted_splits, inst_of, t0, k, feature_dir, gfp_cfg, window_sec, peak_ts_range=peak_ts_range
        )

    write_manifest(
        run_id,
        {
            "run_id": run_id,
            "config_sha256": config_sha256(),
            "snapml_version": snapml_version(),
            "partition": args.partition,
            "splits": sorted(wanted_splits),
            "round_window_sec": window_sec,
            "t0": t0,
            "feature_columns": feature_columns_per_config,
        },
    )
    (repo_path(cfg["paths"]["results"]) / "runs" / ".last_run_id").write_text(
        run_id, encoding="utf-8"
    )
    logger.info("Wrote feature tables and manifest for run %s", run_id)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
