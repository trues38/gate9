#!/bin/bash
# BTC Macro Engine - VPS Setup Script
#
# Usage:
#   1. Clone repo to VPS
#   2. Copy .env.example to .env and configure
#   3. Run: ./deploy/setup-vps.sh
#
# Supports: Ubuntu 20.04+, Debian 11+

set -e

echo "=========================================="
echo "BTC Macro Engine - VPS Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run as regular user (not root)"
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[1/5] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

echo "[2/5] Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/5] Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> IMPORTANT: Edit .env file with your credentials!"
    echo "    nano $PROJECT_DIR/.env"
    echo ""
fi

echo "[5/5] Installing systemd service..."
sudo cp deploy/btc-macro.service /etc/systemd/system/
sudo sed -i "s|/home/ubuntu|$HOME|g" /etc/systemd/system/btc-macro.service
sudo systemctl daemon-reload

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure notifications:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Test notifications:"
echo "   source venv/bin/activate"
echo "   python src/btc_engine/service.py --test"
echo ""
echo "3. Start service:"
echo "   sudo systemctl enable btc-macro"
echo "   sudo systemctl start btc-macro"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status btc-macro"
echo "   journalctl -u btc-macro -f"
echo ""
