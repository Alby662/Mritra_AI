#!/usr/bin/env bash
# ==============================================================================
# deploy/k8s/generate_k8s_secrets.sh
# Generates a production Kubernetes Secret manifest from local secrets/ directory
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SECRETS_DIR="${REPO_DIR}/secrets"
OUTPUT_FILE="${SCRIPT_DIR}/secrets.yaml"

if [[ ! -d "${SECRETS_DIR}" ]]; then
    echo "Error: secrets directory not found at ${SECRETS_DIR}"
    exit 1
fi

echo "==> Creating Kubernetes mTLS Secret manifest from ${SECRETS_DIR}..."

kubectl create secret generic mritra-mtls-secrets \
    --namespace mritra-aml \
    --from-file="${SECRETS_DIR}" \
    --dry-run=client \
    -o yaml > "${OUTPUT_FILE}"

echo "==> Successfully written to ${OUTPUT_FILE}"
echo "==> Apply to cluster with: kubectl apply -f ${OUTPUT_FILE}"
