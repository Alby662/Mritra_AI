"""Build per-config, per-institution feature tables (PREREGISTRATION §5).

Uses mritra/features/views.py as the single source of truth for which edges each
configuration sees, then computes GFP + behavioural features on that edge scope (and
network features, for C3, per-institution -- see note below). Writes
results/runs/<run_id>/features/<config>/<scope>.parquet and a run manifest. Does not train
anything (scripts/train_models.py does that) and does not compute metrics
(scripts/run_eval.py does).

C3's network features are NOT built here: they require a live round-by-round enclave
exchange (mritra.services.enclave_service.EnclaveService), not a single offline batch call,
so C3's table is C1's table only -- a config-audit / schema placeholder for the network
feature columns it will eventually gain, not real boundary values. Building C3's network
features offline means replaying the protocol end to end, which is future work, not part of
this change.
"""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from mritra.config import config_sha256, load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.features.behaviour import compute_behavioural_features
from mritra.features.graph_gfp import compute_gfp_features, load_gfp_config
from mritra.features.views import feature_view
from mritra.protocol.rounds import round_window_sec
from mritra.runs import new_run_id, run_dir, snapml_version, write_manifest

logger = logging.getLogger("build_features")


def _t0(df: pd.DataFrame) -> int:
    """Global round-zero anchor: first TRAIN timestamp (PROTOCOL.md §10, offline runs).

    The same t0 is used for every configuration and every institution's view so that
    round N means the identical wall-clock window everywhere (mritra.protocol.rounds).
    """
    return int(df.loc[df["split"] == "train", "ts"].min())


def _combined_features(
    edges: pd.DataFrame, t0: int, gfp_cfg: dict, window_sec: int
) -> pd.DataFrame:
    gfp_feats = compute_gfp_features(edges, t0, gfp_cfg, window_sec)
    behav_feats = compute_behavioural_features(edges)
    return gfp_feats.join(behav_feats, how="outer")


def build_config_features(
    config: str,
    df: pd.DataFrame,
    t0: int,
    k: int,
    feature_dir,
    gfp_cfg: dict,
    window_sec: int,
) -> dict[str, list[str]]:
    feature_columns: dict[str, list[str]] = {}

    if config in ("C1", "C3"):
        for bank_id in range(k):
            view = feature_view(config if config == "C1" else "C1", df, bank_id=bank_id)
            combined = _combined_features(view.edges, t0, gfp_cfg, window_sec)
            out_path = feature_dir / config / f"bank_{bank_id}.parquet"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            combined.to_parquet(out_path)
            feature_columns[str(bank_id)] = list(combined.columns)
            logger.info(
                "%s bank %d: %d rows, %d cols -> %s",
                config,
                bank_id,
                len(combined),
                combined.shape[1],
                out_path,
            )
    else:  # C4
        view = feature_view("C4", df)
        combined = _combined_features(view.edges, t0, gfp_cfg, window_sec)
        out_path = feature_dir / "C4" / "all.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(out_path)
        feature_columns["all"] = list(combined.columns)
        logger.info("C4: %d rows, %d cols -> %s", len(combined), combined.shape[1], out_path)

    return feature_columns


def main() -> None:
    parser = argparse.ArgumentParser(description="Build C1/C3/C4 feature tables.")
    parser.add_argument("--partition", choices=["P1", "P2"], default="P1")
    parser.add_argument("--configs", default="C1,C3,C4")
    parser.add_argument("--run-id", default=None)
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

    df = pd.read_parquet(parquet / "trans.parquet")
    wanted_splits = set(args.splits.split(","))
    df = df[df["split"].isin(wanted_splits)].copy()
    part_cfg = cfg["partitions"][args.partition]
    inst_of = make_partition(df, part_cfg["method"], k, seed=part_cfg.get("seed"))
    df = add_institutions(df, inst_of)
    t0 = _t0(df)

    gfp_cfg = load_gfp_config()
    window_sec = round_window_sec()

    run_id = args.run_id or new_run_id()
    feature_dir = run_dir(run_id) / "features"

    feature_columns_per_config = {}
    for config in args.configs.split(","):
        feature_columns_per_config[config] = build_config_features(
            config, df, t0, k, feature_dir, gfp_cfg, window_sec
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
