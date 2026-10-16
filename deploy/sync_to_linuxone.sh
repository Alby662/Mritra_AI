#!/usr/bin/env bash
# ==============================================================================
# deploy/sync_to_linuxone.sh
# One-command synchronization of Mritra AI to remote IBM LinuxONE (s390x) VM
#
# Usage:
#   ./deploy/sync_to_linuxone.sh <user@host> [path/to/key.pem] [remote_dir]
#
# Examples:
#   ./deploy/sync_to_linuxone.sh linux1@192.168.1.100 ~/.ssh/id_rsa
#   ./deploy/sync_to_linuxone.sh root@linuxone.example.com
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <user@host> [ssh_key_path] [remote_destination_dir]"
    echo "Example: $0 linux1@148.100.x.x ~/.ssh/linuxone.key /opt/mritra"
    exit 1
fi

REMOTE_TARGET="$1"
SSH_KEY="${2:-}"
REMOTE_DIR="${3:-/home/linux1/Mritra_AI}"

SSH_OPTS=""
if [[ -n "${SSH_KEY}" ]]; then
    SSH_OPTS="-i ${SSH_KEY}"
fi

echo "==> Preparing production build before sync..."
cd "${REPO_DIR}/dashboard" && npm run build
cd "${REPO_DIR}"

echo "==> Syncing Mritra codebase and artifacts to IBM LinuxONE (${REMOTE_TARGET}:${REMOTE_DIR})..."

rsync -avz --progress \
    ${SSH_OPTS:+-e "ssh ${SSH_OPTS}"} \
    --exclude '.git/' \
    --exclude 'dashboard/node_modules/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    "${REPO_DIR}/" "${REMOTE_TARGET}:${REMOTE_DIR}/"

echo "==> Sync completed successfully!"
echo "==> To deploy and launch on LinuxONE, execute:"
echo "    ssh ${SSH_OPTS} ${REMOTE_TARGET} 'cd ${REMOTE_DIR} && chmod +x deploy/deploy_linuxone.sh && ./deploy/deploy_linuxone.sh'"
