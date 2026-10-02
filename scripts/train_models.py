"""Train LightGBM uniformly across C1/C3/C4 (PREREGISTRATION §5, mritra/models/train.py).

Calls the same train_lightgbm() for every configuration and every seed -- same grid,
same early-stopping-on-validation, same scale_pos_weight rule, same threshold search.
Only X/y (which features, which edge scope) differ between configurations; that
difference lives entirely in scripts/build_features.py's output, not here.

Requires results/runs/<run_id>/features/ to already exist (scripts/build_features.py).
"""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from mritra.config import load_config, repo_path
from mritra.models.train import save_model, train_lightgbm
from mritra.runs import run_dir, write_manifest

logger = logging.getLogger("train_models")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightGBM uniformly across configs.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--configs", default="C1,C3,C4")
    args = parser.parse_args()

    cfg = load_config()
    parquet = repo_path(cfg["paths"]["parquet"])
    trans = pd.read_parquet(parquet / "trans.parquet").set_index("row_id")[["split", "is_laund"]]

    rdir = run_dir(args.run_id)
    feature_dir = rdir / "features"
    model_dir = rdir / "models"

    seeds = cfg["model"]["seeds"]
    grid = cfg["model"]["grid"]

    run_info_per_config: dict[str, dict] = {}
    for config in args.configs.split(","):
        config_dir = feature_dir / config
        if not config_dir.is_dir():
            logger.warning("No feature tables for %s at %s -- skipping", config, config_dir)
            continue

        for scope_path in sorted(config_dir.glob("*.parquet")):
            scope_name = scope_path.stem
            feats = pd.read_parquet(scope_path)
            joined = feats.join(trans, how="inner")

            train_mask = joined["split"] == "train"
            val_mask = joined["split"] == "val"
            feature_cols = [c for c in joined.columns if c not in ("split", "is_laund")]
            X_train = joined.loc[train_mask, feature_cols]
            y_train = joined.loc[train_mask, "is_laund"].to_numpy()
            X_val = joined.loc[val_mask, feature_cols]
            y_val = joined.loc[val_mask, "is_laund"].to_numpy()

            for seed in seeds:
                model, threshold, run_info = train_lightgbm(
                    X_train, y_train, X_val, y_val, seed=seed, grid_cfg=grid
                )
                out_path = model_dir / config / scope_name / f"seed_{seed}.txt"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                save_model(model, out_path)
                run_info["threshold"] = threshold
                run_info_per_config.setdefault(config, {}).setdefault(scope_name, {})[str(seed)] = (
                    run_info
                )
                logger.info(
                    "%s/%s seed=%d: pr_auc=%.4f threshold=%.3f -> %s",
                    config,
                    scope_name,
                    seed,
                    run_info["val_pr_auc"],
                    threshold,
                    out_path,
                )

    write_manifest(args.run_id, {"train_run_info": run_info_per_config})
    logger.info("Training complete for run %s", args.run_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
