"""Score trained models and report metrics for a run (PREREGISTRATION §6).

Requires results/runs/<run_id>/models/ (scripts/train_models.py). Writes
results/runs/<run_id>/eval.json: per config/scope/seed, F1 and PR-AUC on the evaluated
split (mritra.eval.metrics), each paired with the dense-day sensitivity variant
(mritra.eval.sensitivity) reported alongside the primary (full-split) result, never in
place of it. C1 additionally gets a cross-bank evaluation: the max of its two
institutions' scores for each cross-bank transaction (PREREGISTRATION §5,
mritra.models.score.cross_bank_max_score), thresholded on this same split. If C1, C3 and
C4 are all present for one run, G is reported with a bootstrap CI and undefined-share
(mritra.eval.bootstrap.bootstrap_gap_recovered) on the cross-bank subset.

Defaults to the validation split (CLAUDE.md §8: don't evaluate on the test period during
development); --split test requires --confirm-test-split.
"""

from __future__ import annotations

import argparse
import json
import logging

import lightgbm as lgb
import numpy as np
import pandas as pd

from mritra.config import load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.eval.bootstrap import bootstrap_gap_recovered
from mritra.eval.metrics import compute_subset_metrics
from mritra.eval.sensitivity import dense_days_from_data_stats, evaluate_with_sensitivity
from mritra.models.score import cross_bank_max_score, score_transactions
from mritra.models.train import _optimal_threshold
from mritra.runs import read_manifest, run_dir, write_manifest

logger = logging.getLogger("run_eval")


def _subset_metrics_dict(y_true: np.ndarray, pred: np.ndarray, prob: np.ndarray) -> dict:
    m = compute_subset_metrics(y_true, pred, prob, "eval")
    return {
        "n_samples": m.n_samples,
        "n_positive": m.n_positive,
        "f1_minority": m.f1_minority,
        "pr_auc": m.pr_auc,
    }


def evaluate_c1_cross_bank(
    scores_by_inst: dict[int, pd.DataFrame],
    cross_txns: pd.DataFrame,
    y_true: pd.Series,
) -> dict:
    """C1's cross-bank score: max of its two institutions' probabilities
    (PREREGISTRATION §5), threshold chosen on this same (evaluated) split to maximise
    minority-class F1 (same rule as every other configuration's own threshold choice --
    PREREGISTRATION §5: "chosen per configuration... to maximise minority-class F1"),
    then F1/PR-AUC on the cross-bank subset.

    Note: cross_bank_max_score()'s own `pred` column uses a hardcoded 0.5 threshold: not
    used here, since C1's cross-bank threshold must be chosen the same way every other
    configuration's is, not hardcoded. This function thresholds `prob` itself instead.
    """
    scored = cross_bank_max_score(scores_by_inst, cross_txns)
    if scored.empty:
        return {"n_samples": 0, "n_positive": 0, "f1_minority": 0.0, "pr_auc": 0.0}

    y = y_true.reindex(scored["row_id"]).to_numpy()
    probs = scored["prob"].to_numpy()
    threshold = _optimal_threshold(y, probs)
    preds = (probs >= threshold).astype(int)

    result = _subset_metrics_dict(y, preds, probs)
    result["threshold"] = threshold
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Score trained models and report metrics.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--split",
        choices=["train", "val", "test"],
        default="val",
        help="Split to evaluate on. Defaults to validation.",
    )
    parser.add_argument(
        "--confirm-test-split",
        action="store_true",
        help="Required in addition to --split test; evaluating on the test split during "
        "development is against CLAUDE.md §8.",
    )
    args = parser.parse_args()

    if args.split == "test" and not args.confirm_test_split:
        parser.error("evaluating on the test split requires --split test --confirm-test-split")

    cfg = load_config()
    k = cfg["institutions"]["k"]
    parquet = repo_path(cfg["paths"]["parquet"])

    trans = pd.read_parquet(parquet / "trans.parquet")
    inst_of = make_partition(trans, cfg["partitions"]["P1"]["method"], k)
    trans = add_institutions(trans, inst_of)
    trans = trans.set_index("row_id", drop=False)
    split_rows = trans[trans["split"] == args.split]
    y_true_all = split_rows["is_laund"]
    cross_txns = split_rows[split_rows["cross"]][["row_id", "from_inst", "to_inst"]]

    dense_days = dense_days_from_data_stats()

    rdir = run_dir(args.run_id)
    manifest = read_manifest(args.run_id)
    train_run_info = manifest.get("train_run_info", {})

    results: dict[str, dict] = {}
    # scores_by_inst[config][seed][bank_id] = scored df, for C1's cross-bank aggregation.
    scores_by_inst: dict[str, dict[str, dict[int, pd.DataFrame]]] = {}

    for config, scopes in train_run_info.items():
        feature_dir = rdir / "features" / config
        for scope_name, per_seed in scopes.items():
            feats = pd.read_parquet(feature_dir / f"{scope_name}.parquet")
            split_feats = feats[feats.index.isin(split_rows.index)]
            eval_df = split_feats.join(split_rows[["ts", "is_laund"]], how="inner")

            for seed, run_info in per_seed.items():
                model_path = rdir / "models" / config / scope_name / f"seed_{seed}.txt"
                model = lgb.Booster(model_file=str(model_path))
                scored = score_transactions(model, split_feats, threshold=run_info["threshold"])
                scored = scored.set_index(pd.Index(split_feats.index, name="row_id"), drop=False)

                if config.startswith("C") and config != "C2" and scope_name.startswith("bank_"):
                    bank_id = int(scope_name.removeprefix("bank_"))
                    scores_by_inst.setdefault(config, {}).setdefault(seed, {})[bank_id] = scored

                def _eval_fn(df: pd.DataFrame, scored: pd.DataFrame = scored) -> dict:
                    pred = scored.reindex(df.index)["pred"].to_numpy()
                    prob = scored.reindex(df.index)["prob"].to_numpy()
                    return _subset_metrics_dict(df["is_laund"].to_numpy(), pred, prob)

                sens = evaluate_with_sensitivity(eval_df, _eval_fn, dense_days=dense_days)
                results.setdefault(config, {}).setdefault(scope_name, {})[seed] = sens
                logger.info(
                    "%s/%s seed=%s: F1=%.4f PR-AUC=%.4f (n=%d, pos=%d); sensitivity n=%d",
                    config,
                    scope_name,
                    seed,
                    sens["primary"]["f1_minority"],
                    sens["primary"]["pr_auc"],
                    sens["primary"]["n_samples"],
                    sens["primary"]["n_positive"],
                    sens["sensitivity_rows_kept"],
                )

    # C1 cross-bank evaluation (PREREGISTRATION §5), per seed.
    c1_cross_bank: dict[str, dict] = {}
    for seed, by_inst in scores_by_inst.get("C1", {}).items():
        c1_cross_bank[seed] = evaluate_c1_cross_bank(by_inst, cross_txns, y_true_all)

    # G with bootstrap CI (PREREGISTRATION §6.2), on the cross-bank subset, per seed --
    # only when C1, C3 and C4 are all available for the same seed. C3's offline feature
    # build is not implemented yet (scripts/build_features.py's docstring), so this is
    # currently always empty; reported honestly as such rather than faked with a stand-in.
    gap_by_seed: dict[str, dict] = {}
    gap_note = None
    c3_by_seed = scores_by_inst.get("C3", {})
    c4_by_seed = scores_by_inst.get("C4", {})
    for seed, c1_by_inst in scores_by_inst.get("C1", {}).items():
        if seed not in c3_by_seed or seed not in c4_by_seed or "all" not in c4_by_seed[seed]:
            gap_note = (
                "C3 is not available for this run (scripts/build_features.py does not "
                "build C3's network features offline yet) -- G cannot be computed"
            )
            continue
        c1_scored = cross_bank_max_score(c1_by_inst, cross_txns)
        c3_scored = cross_bank_max_score(c3_by_seed[seed], cross_txns)
        if c1_scored.empty or c3_scored.empty:
            continue
        c4_scored = c4_by_seed[seed]["all"].reindex(c1_scored["row_id"])
        c3_scored = c3_scored.set_index("row_id", drop=False).reindex(c1_scored["row_id"])
        y = y_true_all.reindex(c1_scored["row_id"]).to_numpy()
        prob_c1, prob_c3, prob_c4 = (
            c1_scored["prob"].to_numpy(),
            c3_scored["prob"].to_numpy(),
            c4_scored["prob"].to_numpy(),
        )
        threshold_c1 = _optimal_threshold(y, prob_c1)
        threshold_c3 = _optimal_threshold(y, prob_c3)
        threshold_c4 = _optimal_threshold(y, prob_c4)
        ci = bootstrap_gap_recovered(
            y, prob_c1, prob_c3, prob_c4, threshold_c1, threshold_c3, threshold_c4
        )
        gap_by_seed[seed] = {
            "g_point_estimate": ci.point_estimate,
            "g_ci_lower": ci.ci_lower,
            "g_ci_upper": ci.ci_upper,
            "n_undefined": ci.n_undefined,
            "undefined_share": ci.undefined_share,
        }

    output = {
        "split": args.split,
        "results": results,
        "c1_cross_bank": c1_cross_bank,
        "gap_recovered": gap_by_seed,
        "gap_recovered_note": gap_note,
    }
    (rdir / "eval.json").write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(args.run_id, {"eval_written": True, "eval_split": args.split})
    logger.info("Wrote %s", rdir / "eval.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
