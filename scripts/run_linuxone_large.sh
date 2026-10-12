#!/usr/bin/env bash
# ==============================================================================
# scripts/run_linuxone_large.sh
# Automated IBM LinuxONE (s390x) Cluster Runbook for HI-Large (180M rows)
#
# Leverages:
#  - IBM Z on-chip AI accelerator (Integrated Accelerator for AI / NNPA)
#  - IBM Z Accelerated for Snap ML container (icr.io/ibmz/ibmz-accelerated-for-snapml)
#  - High core counts with OpenMP & thread affinity
#  - Out-of-core sorted Parquet streaming with 5M row batches
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

LOG_DIR="${REPO_DIR}/results/cluster_logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
RUN_LOG="${LOG_DIR}/linuxone_large_${TIMESTAMP}.log"

exec > >(tee -a "${RUN_LOG}") 2>&1

echo "===================================================================="
echo " Starting Mritra AI Pipeline on IBM LinuxONE (HI-Large 180M)"
echo " Timestamp: $(date -u --iso-8601=seconds)"
echo " Workspace: ${REPO_DIR}"
echo "===================================================================="

# ------------------------------------------------------------------------------
# 1. System & Architecture Diagnostics
# ------------------------------------------------------------------------------
ARCH=$(uname -m)
CORES=$(nproc || echo 4)
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}' || echo 16)

echo "[INFO] Architecture: ${ARCH}"
echo "[INFO] CPU Cores:    ${CORES}"
echo "[INFO] Total RAM:    ${TOTAL_RAM_GB} GB"

if [[ "${ARCH}" == "s390x" ]]; then
    echo "[INFO] Native IBM Z / LinuxONE hardware detected."
    if grep -iq "type.*z16\|type.*3931\|type.*3932" /proc/sysinfo 2>/dev/null; then
        echo "[INFO] IBM z16 / LinuxONE 4 detected - On-chip AI Acceleration active!"
    else
        echo "[INFO] Machine sysinfo: $(grep -i 'type' /proc/sysinfo 2>/dev/null || echo 'generic s390x')"
    fi
else
    echo "[WARN] Not running natively on s390x (detected: ${ARCH}). Running in local/test mode."
fi

# ------------------------------------------------------------------------------
# 2. Performance & Threading Optimizations
# ------------------------------------------------------------------------------
export OMP_NUM_THREADS="${CORES}"
export SNAPML_NUM_THREADS="${CORES}"
export OPENBLAS_NUM_THREADS="${CORES}"
export MKL_NUM_THREADS="${CORES}"
export VECLIB_MAXIMUM_THREADS="${CORES}"
export NUMEXPR_NUM_THREADS="${CORES}"
export DUCKDB_THREADS="${CORES}"
export PYTHONUNBUFFERED=1

echo "[INFO] Threading concurrency set to ${CORES} threads across OpenMP/SnapML/DuckDB."

# ------------------------------------------------------------------------------
# 3. Data Ingestion: Verify & Link HI-Large Parquet
# ------------------------------------------------------------------------------
PARQUET_DIR="${REPO_DIR}/data/parquet"
LARGE_PARQUET="${PARQUET_DIR}/trans_large.parquet"
TARGET_PARQUET="${PARQUET_DIR}/trans.parquet"

if [[ -f "${LARGE_PARQUET}" ]]; then
    echo "[INFO] Found dedicated HI-Large file: ${LARGE_PARQUET}"
    # If target is currently smaller or points elsewhere, point it to large
    if [[ ! -f "${TARGET_PARQUET}" ]] || [[ "$(stat -c%s "${TARGET_PARQUET}" 2>/dev/null)" -lt "$(stat -c%s "${LARGE_PARQUET}" 2>/dev/null)" ]]; then
        echo "[INFO] Linking ${LARGE_PARQUET} -> ${TARGET_PARQUET} for full cluster run..."
        ln -sf "${LARGE_PARQUET}" "${TARGET_PARQUET}"
    fi
elif [[ -f "${TARGET_PARQUET}" ]]; then
    FILE_SIZE_GB=$(du -bg "${TARGET_PARQUET}" | cut -f1)
    echo "[INFO] Using existing ${TARGET_PARQUET} (${FILE_SIZE_GB} GB)."
else
    echo "[ERROR] No HI-Large parquet dataset found at ${TARGET_PARQUET} or ${LARGE_PARQUET}!"
    exit 1
fi

# Ensure patterns file is linked if large patterns exists
if [[ -f "${PARQUET_DIR}/patterns_large.parquet" ]]; then
    ln -sf "${PARQUET_DIR}/patterns_large.parquet" "${PARQUET_DIR}/patterns.parquet"
fi

# ------------------------------------------------------------------------------
# 4. Container Execution vs Native Environment
# ------------------------------------------------------------------------------
CONTAINER_IMAGE="icr.io/ibmz/ibmz-accelerated-for-snapml:latest"
USE_CONTAINER=false

if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    USE_CONTAINER=true
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    USE_CONTAINER=true
fi

# If inside container already, run natively
if [[ -f "/.dockerenv" ]] || grep -q 'container' /proc/1/environ 2>/dev/null; then
    USE_CONTAINER=false
fi

# ------------------------------------------------------------------------------
# 5. Pipeline Execution Functions
# ------------------------------------------------------------------------------
run_pipeline_native() {
    echo "--------------------------------------------------------------------"
    echo "[STAGE 1/3] Building Features on HI-Large (180M rows)..."
    echo "--------------------------------------------------------------------"
    START_FEAT=$(date +%s)
    /usr/bin/time -v uv run python scripts/build_features.py --configs C1,C3,C4
    END_FEAT=$(date +%s)
    echo "[SUCCESS] Feature extraction completed in $((END_FEAT - START_FEAT)) seconds."

    LATEST_RUN_ID=$(cat results/runs/.last_run_id)
    echo "[INFO] Active Cluster Run ID: ${LATEST_RUN_ID}"

    echo "--------------------------------------------------------------------"
    echo "[STAGE 2/3] Training Models across C1, C3, and C4 (is_unbalance=True active)..."
    echo "--------------------------------------------------------------------"
    START_TRAIN=$(date +%s)
    /usr/bin/time -v uv run python scripts/train_models.py --run-id "${LATEST_RUN_ID}" --configs C1,C3,C4
    END_TRAIN=$(date +%s)
    echo "[SUCCESS] Model training completed in $((END_TRAIN - START_TRAIN)) seconds."

    echo "--------------------------------------------------------------------"
    echo "[STAGE 3/3] Running Comprehensive Evaluation (Validation Split)..."
    echo "--------------------------------------------------------------------"
    START_EVAL=$(date +%s)
    /usr/bin/time -v uv run python scripts/run_eval.py --run-id "${LATEST_RUN_ID}" --split val
    END_EVAL=$(date +%s)
    echo "[SUCCESS] Evaluation completed in $((END_EVAL - START_EVAL)) seconds."

    echo "===================================================================="
    echo " Pipeline Finished Successfully!"
    echo " Results: results/runs/${LATEST_RUN_ID}/eval.json"
    echo "===================================================================="
    
    if [[ -f "results/runs/${LATEST_RUN_ID}/eval.json" ]]; then
        python3 -c "
import json
with open('results/runs/${LATEST_RUN_ID}/eval.json') as f:
    d = json.load(f)
print('Gap Recovered G:', d.get('gap_recovered'))
"
    fi
}

run_pipeline_container() {
    echo "[INFO] Launching inside ${CONTAINER_CMD} container: ${CONTAINER_IMAGE}"
    ${CONTAINER_CMD} pull "${CONTAINER_IMAGE}" || echo "[WARN] Pull failed, trying local cached image..."
    
    ${CONTAINER_CMD} run --rm -it \
        --ipc=host \
        --ulimit memlock=-1:-1 \
        -e OMP_NUM_THREADS="${CORES}" \
        -e SNAPML_NUM_THREADS="${CORES}" \
        -e DUCKDB_THREADS="${CORES}" \
        -v "${REPO_DIR}":/work:Z \
        -w /work \
        "${CONTAINER_IMAGE}" \
        bash -c "pip install -r requirements-services.txt 2>/dev/null || true; ./scripts/run_linuxone_large.sh --native"
}

# ------------------------------------------------------------------------------
# 6. Main Dispatch
# ------------------------------------------------------------------------------
if [[ "${1:-}" == "--native" ]] || [[ "${USE_CONTAINER}" == "false" ]]; then
    run_pipeline_native
else
    run_pipeline_container
fi
