"""Generate results/config_audit.json (CLAUDE.md rule 9: no hand-typed numbers).

Per configuration: edge scope, feature columns, hyperparameter grid, early-stopping set,
class-imbalance handling, seeds, boosting rounds. Confirms or denies "C1-C4 differ only in
the features they can see" (PREREGISTRATION §5) -- see
tests/test_config_audit.py::test_configs_identical_except_feature_columns_and_edge_scope.

Does not train or touch the real dataset: GFP's column count is measured on a tiny
synthetic edge list (cheap, no snapml run at dataset scale needed) so the real number is
reported, not guessed.
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from mritra.config import config_sha256, load_config, repo_path
from mritra.features.behaviour import FEATURE_COLUMNS as BEHAVIOUR_FEATURE_COLUMNS
from mritra.features.graph_gfp import compute_gfp_features, gfp_feature_names, load_gfp_config
from mritra.features.network import network_feature_names
from mritra.runs import snapml_version

logger = logging.getLogger("config_audit")

# mritra/services/bank_service.py:prepare_boundary_summaries hardcodes a 6-dim zero-vector
# fallback -- the real schema (PROTOCOL.md's configs/protocol.yaml) does not exist in this
# repo yet, so this is that same placeholder width, not a confirmed value.
_NETWORK_SUMMARY_DIM_PLACEHOLDER = 6


def _toy_edges(n: int = 6) -> pd.DataFrame:
    accounts = [f"A{i}" for i in range(4)]
    rng = np.random.default_rng(0)
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
                "ts": 1_000 + i * 10,
                "amt_paid": 10.0 + i,
            }
        )
    return pd.DataFrame(rows)


def _gfp_n_feat() -> int:
    gfp_cfg = load_gfp_config()
    out = compute_gfp_features(_toy_edges(), t0=0, gfp_cfg=gfp_cfg, round_window_sec=3600)
    return out.shape[1]


def build_config_audit() -> dict:
    cfg = load_config()
    model_cfg = cfg["model"]
    gfp_cfg = load_gfp_config()

    gfp_n_feat = _gfp_n_feat()
    gfp_cols = gfp_feature_names(gfp_n_feat, gfp_cfg)
    behaviour_cols = list(BEHAVIOUR_FEATURE_COLUMNS)
    net_cols = network_feature_names(_NETWORK_SUMMARY_DIM_PLACEHOLDER)

    shared = {
        "model_family": model_cfg["family"],
        "hyperparameter_grid": model_cfg["grid"],
        "early_stopping_set": "validation",
        "early_stopping_rounds": 50,
        "seeds": model_cfg["seeds"],
        "boosting_rounds": model_cfg["grid"]["n_estimators"],
        "class_imbalance_handling": "scale_pos_weight = n_neg / n_pos on the training set",
        "threshold_objective": model_cfg["threshold_objective"],
    }

    return {
        "config_sha256": config_sha256(),
        "snapml_version": snapml_version(),
        "gfp_n_feat_measured_on_toy_data": gfp_n_feat,
        "network_summary_dim_placeholder": _NETWORK_SUMMARY_DIM_PLACEHOLDER,
        "configs": {
            "C1": {
                **shared,
                "edge_scope": (
                    "Institution b's own edges: from_inst==b or to_inst==b (its internal "
                    "transactions and its own side of cross-bank transactions). Own "
                    "accounts only."
                ),
                "feature_columns": gfp_cols + behaviour_cols,
            },
            "C2": {
                **shared,
                "edge_scope": (
                    "Not implemented (mritra.features.views.feature_view raises "
                    "NotImplementedError)."
                ),
                "feature_columns": [],
            },
            "C3": {
                **shared,
                "edge_scope": (
                    "Same as C1 (institution b's own edges, own accounts), plus enclave "
                    "network features for those same accounts."
                ),
                "feature_columns": gfp_cols + behaviour_cols + net_cols,
            },
            "C4": {
                **shared,
                "edge_scope": "Every edge, every account -- no institution restriction.",
                "feature_columns": gfp_cols + behaviour_cols,
            },
        },
    }


def main() -> None:
    cfg = load_config()
    audit = build_config_audit()
    out_path = repo_path(cfg["paths"]["results"]) / "config_audit.json"
    out_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
