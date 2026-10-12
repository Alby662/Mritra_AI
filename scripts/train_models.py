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
from mritra.runs import read_manifest, run_dir, write_manifest

logger = logging.getLogger("train_models")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightGBM uniformly across configs.")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run ID to train models for. Defaults to results/runs/.last_run_id.",
    )
    parser.add_argument("--configs", default="C1,C3,C4")
    args = parser.parse_args()

    cfg = load_config()
    run_id = args.run_id
    if not run_id:
        last_run_path = repo_path(cfg["paths"]["results"]) / "runs" / ".last_run_id"
        if last_run_path.exists():
            run_id = last_run_path.read_text(encoding="utf-8").strip()
        else:
            parser.error("No --run-id provided and results/runs/.last_run_id does not exist")

    parquet = repo_path(cfg["paths"]["parquet"])
    trans = pd.read_parquet(parquet / "trans.parquet")

    k = cfg["institutions"]["k"]
    from mritra.data.partition import add_institutions, make_partition

    inst_of = make_partition(trans, cfg["partitions"]["P1"]["method"], k)
    trans = add_institutions(trans, inst_of)
    trans = trans.set_index("row_id", drop=False)

    val_split_rows = trans[trans["split"] == "val"]
    val_cross_txns = val_split_rows[val_split_rows["cross"]][["row_id", "from_inst", "to_inst"]]
    val_y_true = val_split_rows["is_laund"]
    val_scores_by_inst: dict[str, dict[int, dict[int, pd.DataFrame]]] = {}

    rdir = run_dir(run_id)
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
            import pyarrow.parquet as pq

            pf = pq.ParquetFile(scope_path)
            schema = pf.schema_arrow
            feature_cols = schema.names
            if "row_id" in feature_cols:
                feature_cols.remove("row_id")
            elif "__index_level_0__" in feature_cols:
                feature_cols.remove("__index_level_0__")

            # Read just the index to align masks
            idx = pf.read(["row_id"]).column("row_id").to_numpy()

            train_mask = (trans.loc[idx, "split"] == "train").to_numpy()
            val_mask = (trans.loc[idx, "split"] == "val").to_numpy()
            y = trans.loc[idx, "is_laund"].to_numpy()

            y_train = y[train_mask].copy()
            y_val = y[val_mask].copy()

            import numpy as np

            n_train = train_mask.sum()
            n_val = val_mask.sum()
            n_cols = len(feature_cols)

            X_train_arr = np.empty((n_train, n_cols), dtype=np.float32)
            X_val_arr = np.empty((n_val, n_cols), dtype=np.float32)

            for i, col in enumerate(feature_cols):
                col_data = pf.read([col]).column(col).to_numpy()
                X_train_arr[:, i] = col_data[train_mask]
                X_val_arr[:, i] = col_data[val_mask]

            X_train = pd.DataFrame(X_train_arr, columns=feature_cols)
            X_val = pd.DataFrame(X_val_arr, columns=feature_cols)

            val_row_ids = idx[val_mask]
            del X_train_arr, X_val_arr, col_data, y, train_mask, val_mask, pf, idx
            import gc

            gc.collect()

            for seed in seeds:
                model, threshold, run_info = train_lightgbm(
                    X_train,
                    y_train,
                    X_val,
                    y_val,
                    seed=seed,
                    grid_cfg=grid,
                    feature_name=feature_cols,
                )
                out_path = model_dir / config / scope_name / f"seed_{seed}.txt"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                save_model(model, out_path)
                run_info["threshold"] = threshold
                run_info_per_config.setdefault(config, {}).setdefault(scope_name, {})[str(seed)] = (
                    run_info
                )

                if config in ("C1", "C3") and scope_name.startswith("bank_"):
                    bank_id = int(scope_name.removeprefix("bank_"))
                    val_prob = model.predict_proba(X_val)[:, 1]
                    scored_val = pd.DataFrame({"row_id": val_row_ids, "prob": val_prob})
                    val_scores_by_inst.setdefault(config, {}).setdefault(seed, {})[bank_id] = (
                        scored_val
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
                del model
                import gc

                gc.collect()
            del X_train, X_val, y_train, y_val
            gc.collect()

    from mritra.models.score import cross_bank_max_score
    from mritra.models.train import _optimal_threshold

    for config in ["C1", "C3"]:
        if config not in val_scores_by_inst:
            continue
        for seed, inst_scores in val_scores_by_inst[config].items():
            scored = cross_bank_max_score(inst_scores, val_cross_txns)
            if not scored.empty:
                scored_y = val_y_true.loc[scored["row_id"]].to_numpy()
                ensemble_thresh = _optimal_threshold(scored_y, scored["prob"].to_numpy())
                run_info_per_config.setdefault(config, {}).setdefault("cross_bank", {})[
                    str(seed)
                ] = {"threshold": float(ensemble_thresh)}
                logger.info(
                    "%s cross_bank seed=%d: optimal_threshold=%.3f",
                    config,
                    seed,
                    ensemble_thresh,
                )

    manifest = read_manifest(run_id)
    existing_info = manifest.get("train_run_info", {})
    existing_info.update(run_info_per_config)
    write_manifest(run_id, {"train_run_info": existing_info})
    logger.info("Training complete for run %s", run_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
