#!/usr/bin/env bash
# ==============================================================================
# dashboard/deploy/setup-ec2.sh
# One-time initialization script for Ubuntu EC2 instance hosting the Dashboard
# Run this on your EC2 instance once:
#   chmod +x setup-ec2.sh && sudo ./setup-ec2.sh
# ==============================================================================

set -euo pipefail

echo "==> Updating package indices and installing Nginx..."
sudo apt-get update -y
sudo apt-get install -y nginx rsync

echo "==> Setting up web root directory at /var/www/dashboard..."
sudo mkdir -p /var/www/dashboard

# Grant ownership to the current user (ubuntu or ec2-user) and www-data
CURRENT_USER="${SUDO_USER:-$USER}"
sudo chown -R "${CURRENT_USER}:www-data" /var/www/dashboard
sudo chmod -R 775 /var/www/dashboard

echo "==> Configuring Nginx site..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/nginx.conf" ]; then
    sudo cp "${SCRIPT_DIR}/nginx.conf" /etc/nginx/sites-available/dashboard
    sudo ln -sf /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
    # Remove default site if present
    sudo rm -f /etc/nginx/sites-enabled/default
else
    echo "Warning: nginx.conf not found next to script. Please copy it manually to /etc/nginx/sites-available/dashboard"
fi

echo "==> Testing and reloading Nginx..."
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "======================================================================"
echo "EC2 Web Server is configured!"
echo "Web root: /var/www/dashboard"
echo "Deploy user permissions configured for: ${CURRENT_USER}"
echo "======================================================================"
