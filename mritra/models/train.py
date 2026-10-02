"""LightGBM training for C1/C3/C4 configurations (plan §7.2).

Same model family across all configurations; they differ only in which
features they can see.  ``scale_pos_weight`` handles class imbalance.
Grid search on validation PR-AUC.  Threshold chosen to maximise
minority-class F1 on validation.
"""

from __future__ import annotations

import json
import logging
from itertools import product
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score

from mritra.config import load_config

logger = logging.getLogger(__name__)


def _build_grid(grid_cfg: dict[str, list]) -> list[dict[str, Any]]:
    """Expand a grid spec into a list of parameter dicts."""
    keys = list(grid_cfg.keys())
    values = [grid_cfg[k] for k in keys]
    return [dict(zip(keys, combo, strict=True)) for combo in product(*values)]


def _optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Find the threshold that maximises minority-class F1 on the positive class."""
    best_f1 = -1.0
    best_t = 0.5
    for t in np.arange(0.01, 1.0, 0.01):
        preds = (y_prob >= t).astype(int)
        f1 = f1_score(y_true, preds, pos_label=1, zero_division=0.0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    seed: int = 42,
    grid_cfg: dict[str, list] | None = None,
) -> tuple[lgb.LGBMClassifier, float, dict[str, Any]]:
    """Train LightGBM with grid search on validation PR-AUC.

    Parameters
    ----------
    X_train, y_train : training features and labels
    X_val, y_val : validation features and labels
    seed : random seed
    grid_cfg : hyperparameter grid (from experiment.yaml)

    Returns
    -------
    (best_model, optimal_threshold, run_info)
    """
    if grid_cfg is None:
        cfg = load_config()
        grid_cfg = cfg["model"]["grid"]

    # Scale positive weight for class imbalance
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / n_pos if n_pos > 0 else 1.0

    grid = _build_grid(grid_cfg)
    logger.info("Grid search: %d combinations, seed=%d", len(grid), seed)

    best_score = -1.0
    best_model = None
    best_params: dict[str, Any] = {}

    for params in grid:
        model = lgb.LGBMClassifier(
            **params,
            scale_pos_weight=spw,
            random_state=seed,
            verbose=-1,
            n_jobs=-1,
        )
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
        y_prob = model.predict_proba(X_val)[:, 1]
        pr_auc = average_precision_score(y_val, y_prob)

        if pr_auc > best_score:
            best_score = pr_auc
            best_model = model
            best_params = params

    assert best_model is not None
    y_prob_best = best_model.predict_proba(X_val)[:, 1]
    threshold = _optimal_threshold(y_val, y_prob_best)

    run_info = {
        "seed": seed,
        "best_params": best_params,
        "val_pr_auc": float(best_score),
        "optimal_threshold": threshold,
        "scale_pos_weight": float(spw),
        "n_train": len(y_train),
        "n_val": len(y_val),
        "n_pos_train": n_pos,
    }
    logger.info(
        "Best: pr_auc=%.4f threshold=%.3f params=%s",
        best_score,
        threshold,
        best_params,
    )
    return best_model, threshold, run_info


def save_model(model: lgb.LGBMClassifier, path: Path) -> None:
    """Save a trained model."""
    path.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(path))
    logger.info("Saved model to %s", path)


def load_model(path: Path) -> lgb.Booster:
    """Load a trained model."""
    return lgb.Booster(model_file=str(path))
