#!/bin/bash
# BTC Macro Engine - Docker Setup Script
#
# Usage:
#   1. Clone repo to VPS
#   2. Copy .env.example to .env and configure
#   3. Run: ./deploy/setup-docker.sh

set -e

echo "=========================================="
echo "BTC Macro Engine - Docker Setup"
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Please log out and back in, then run this script again."
    exit 0
fi

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing docker-compose..."
    sudo apt-get install -y docker-compose
fi

echo "[1/3] Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> IMPORTANT: Edit .env file with your credentials!"
    echo "    nano $PROJECT_DIR/.env"
    echo ""
    exit 1
fi

echo "[2/3] Building Docker image..."
docker-compose build

echo "[3/3] Testing notification..."
docker-compose run --rm btc-macro python src/btc_engine/service.py --test

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Commands:"
echo ""
echo "  Start:   docker-compose up -d"
echo "  Stop:    docker-compose down"
echo "  Logs:    docker-compose logs -f"
echo "  Test:    docker-compose run --rm btc-macro python src/btc_engine/service.py --test"
echo ""
