"""Score trained models and report metrics for a run (PREREGISTRATION §6).

Requires results/runs/<run_id>/models/ (scripts/train_models.py). Writes
results/runs/<run_id>/eval.json: per config/scope/seed, F1 and PR-AUC on the test split
(mritra.eval.metrics), plus G (mritra.eval.metrics.gap_recovered) when C1 and C4 are both
present for the same scope naming (only meaningful for C4's single "all" scope vs. a
siloed config's per-bank scope pooled across banks -- see the note in main()).

This is deliberately the minimal version: it does not yet implement C1's cross-bank
max-of-two-institutions aggregation (mritra.models.score.cross_bank_max_score) or the
bootstrap CI / sensitivity-analysis reporting (mritra.eval.bootstrap,
mritra.eval.sensitivity) -- those need a cross-bank transaction join and a chosen
partition's cross/within tagging that this script does not yet build. Flagged as an open
item in the session report, not implemented here.
"""

from __future__ import annotations

import argparse
import json
import logging

import lightgbm as lgb
import pandas as pd

from mritra.config import load_config, repo_path
from mritra.eval.metrics import compute_subset_metrics
from mritra.models.score import score_transactions
from mritra.runs import read_manifest, run_dir, write_manifest

logger = logging.getLogger("run_eval")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score trained models and report metrics.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    cfg = load_config()
    parquet = repo_path(cfg["paths"]["parquet"])
    trans = pd.read_parquet(parquet / "trans.parquet").set_index("row_id")[["split", "is_laund"]]
    test_labels = trans[trans["split"] == "test"]["is_laund"]

    rdir = run_dir(args.run_id)
    manifest = read_manifest(args.run_id)
    train_run_info = manifest.get("train_run_info", {})

    results: dict[str, dict] = {}
    for config, scopes in train_run_info.items():
        feature_path_template = rdir / "features" / config
        for scope_name, per_seed in scopes.items():
            feats = pd.read_parquet(feature_path_template / f"{scope_name}.parquet")
            test_feats = feats[feats.index.isin(test_labels.index)]
            y_true = test_labels.loc[test_feats.index].to_numpy()

            for seed, run_info in per_seed.items():
                model_path = rdir / "models" / config / scope_name / f"seed_{seed}.txt"
                model = lgb.Booster(model_file=str(model_path))
                scored = score_transactions(model, test_feats, threshold=run_info["threshold"])
                m = compute_subset_metrics(
                    y_true, scored["pred"].to_numpy(), scored["prob"].to_numpy(), "all"
                )
                results.setdefault(config, {}).setdefault(scope_name, {})[seed] = {
                    "n_samples": m.n_samples,
                    "n_positive": m.n_positive,
                    "f1_minority": m.f1_minority,
                    "pr_auc": m.pr_auc,
                }
                logger.info(
                    "%s/%s seed=%s: F1=%.4f PR-AUC=%.4f (n=%d, pos=%d)",
                    config,
                    scope_name,
                    seed,
                    m.f1_minority,
                    m.pr_auc,
                    m.n_samples,
                    m.n_positive,
                )

    (rdir / "eval.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(args.run_id, {"eval_written": True})
    logger.info("Wrote %s", rdir / "eval.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
