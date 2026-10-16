#!/bin/bash
# ==============================================================================
# Mritra AI - Enterprise Systemd & Logging Installer for IBM LinuxONE (s390x)
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${BLUE}========================================================================${NC}"
echo -e "${BOLD} Installing Enterprise Systemd Daemons & Logrotate on LinuxONE...${NC}"
echo -e "${BOLD}${BLUE}========================================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Setup Logging Directory
echo -e "  • Setting up /var/log/mritra/ logging directory..."
sudo mkdir -p /var/log/mritra
sudo chown -R linux1:linux1 /var/log/mritra
sudo chmod 755 /var/log/mritra

# 2. Kill any old unmanaged nohup uvicorn processes to free up ports
echo -e "  • Stopping existing unmanaged uvicorn processes..."
pkill -f "uvicorn mritra.services" || true
sleep 1

# 3. Copy systemd unit files
echo -e "  • Copying systemd unit files to /etc/systemd/system/..."
sudo cp "${SCRIPT_DIR}/mritra-enclave.service" /etc/systemd/system/
sudo cp "${SCRIPT_DIR}/mritra-bank@.service" /etc/systemd/system/
sudo cp "${SCRIPT_DIR}/mritra.target" /etc/systemd/system/

# 4. Copy logrotate config
echo -e "  • Configuring logrotate in /etc/logrotate.d/mritra..."
sudo cp "${SCRIPT_DIR}/mritra.logrotate" /etc/logrotate.d/mritra
sudo chmod 644 /etc/logrotate.d/mritra

# 5. Reload systemd daemon
echo -e "  • Reloading systemd daemon..."
sudo systemctl daemon-reload

# 6. Enable and Start Services
echo -e "  • Enabling and starting Mritra services..."
sudo systemctl enable mritra-enclave.service
sudo systemctl restart mritra-enclave.service

for i in {0..4}; do
    sudo systemctl enable "mritra-bank@${i}.service"
    sudo systemctl restart "mritra-bank@${i}.service"
done

sudo systemctl enable mritra.target
sudo systemctl restart mritra.target

# 7. Check Status
sleep 2
echo -e "\n${BOLD}=== Systemd Services Health Check ===${NC}"
sudo systemctl is-active mritra-enclave.service && echo -e "  • Enclave Service:       ${GREEN}ACTIVE (Running on :8443)${NC}" || echo -e "  • Enclave Service:       ${RED}FAILED${NC}"

for i in {0..4}; do
    PORT=$((8000 + i))
    sudo systemctl is-active "mritra-bank@${i}.service" && echo -e "  • Bank B${i} Service:         ${GREEN}ACTIVE (Running on :${PORT})${NC}" || echo -e "  • Bank B${i} Service:         ${RED}FAILED${NC}"
done

echo -e "\n${GREEN}✓ Enterprise Daemons & Supervision Successfully Installed!${NC}"
