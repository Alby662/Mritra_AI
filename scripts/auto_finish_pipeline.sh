#!/usr/bin/env bash
# ==============================================================================
# scripts/auto_finish_pipeline.sh
# Automated pipeline runner: completes C3/C4 feature extraction (resuming from
# C1 tables and C3 checkpoint), trains models, evaluates test split, and mines hero chain.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

LOG_FILE="${REPO_DIR}/results/auto_finish.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

RUN_ID="20261011T161246Z"

echo "===================================================================="
echo "[$(date -u)] Starting Automated Pipeline Execution for Run: ${RUN_ID}"
echo "===================================================================="

echo "--------------------------------------------------------------------"
echo "[1/4] Resuming Feature Extraction (C3 alignment & C4 oracle)..."
echo "--------------------------------------------------------------------"
uv run python scripts/build_features.py --run-id "${RUN_ID}" --configs C1,C3,C4

echo "--------------------------------------------------------------------"
echo "[2/4] Training Models across C1, C3, and C4..."
echo "--------------------------------------------------------------------"
uv run python scripts/train_models.py --run-id "${RUN_ID}" --configs C1,C3,C4

echo "--------------------------------------------------------------------"
echo "[3/4] Scoring and Evaluating Static Blind Test Split..."
echo "--------------------------------------------------------------------"
uv run python scripts/run_eval.py --run-id "${RUN_ID}" --split test --confirm-test-split

echo "--------------------------------------------------------------------"
echo "[4/4] Mining Hero Chain for Frontend Demo..."
echo "--------------------------------------------------------------------"
uv run python scripts/find_hero_chain.py --run-id "${RUN_ID}"

echo "===================================================================="
echo "[$(date -u)] Entire ML Pipeline & Artifact Generation Completed!"
echo "===================================================================="

cat <<EOF > results/PIPELINE_COMPLETE.json
{
  "status": "COMPLETED",
  "run_id": "${RUN_ID}",
  "completed_at": "$(date -u --iso-8601=seconds)",
  "eval_file": "results/runs/${RUN_ID}/eval.json",
  "hero_chain_file": "results/demo_hero_chain.json"
}
EOF
