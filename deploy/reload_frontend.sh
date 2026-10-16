#!/bin/bash
# ==============================================================================
# Mritra AI - Zero-Downtime Frontend Rollout & Nginx Hot-Reload
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REMOTE_HOST="148.100.79.186"
REMOTE_USER="linux1"
SSH_KEY="${HOME}/Downloads/mitra.pem"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "\n${BOLD}${BLUE}========================================================================${NC}"
echo -e "${BOLD} Starting Zero-Downtime Rollout to IBM LinuxONE (${REMOTE_HOST})...${NC}"
echo -e "${BOLD}${BLUE}========================================================================${NC}"

# 1. Build Production Frontend Bundle
echo -e "  • Building optimized production bundle in dashboard/..."
cd "${REPO_ROOT}/dashboard"
npm run build

if [[ ! -f "${REPO_ROOT}/dashboard/dist/index.html" ]]; then
    echo -e "  • ${RED}Build failed: dashboard/dist/index.html not found!${NC}"
    exit 1
fi
echo -e "  • ${GREEN}✓ Production build ready.${NC}"

# 2. Rsync dist to Remote LinuxONE
echo -e "  • Syncing static bundle to LinuxONE (${REMOTE_HOST})..."
rsync -avz --delete \
    -e "ssh -o StrictHostKeyChecking=no -i ${SSH_KEY}" \
    "${REPO_ROOT}/dashboard/dist/" \
    "${REMOTE_USER}@${REMOTE_HOST}:/home/linux1/Mritra_AI/dashboard/dist/"

# 3. Hot-Reload Nginx with Zero Downtime
echo -e "  • Validating Nginx config & executing atomic hot-reload..."
ssh -o StrictHostKeyChecking=no -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" << 'EOF'
set -e
sudo nginx -t
sudo nginx -s reload
echo "Nginx hot-reloaded successfully."
EOF

# 4. Probe Remote Endpoint
echo -e "  • Probing remote endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${REMOTE_HOST}/" || echo "FAIL")
if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo -e "  • ${GREEN}✓ Zero-Downtime Rollout Complete! HTTP Status: 200 OK${NC}"
    echo -e "  • Live URL: http://${REMOTE_HOST}/ (and https://${REMOTE_HOST}/)"
else
    echo -e "  • ${RED}Warning: Remote endpoint probe returned status ${HTTP_STATUS}${NC}"
fi
