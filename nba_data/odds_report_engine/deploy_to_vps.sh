#!/bin/bash

##############################################
# Deploy Graph + Odds Report Engine to VPS
##############################################

VPS_HOST="root@141.164.35.214"
VPS_DIR="/opt/g9/nba-collector"
LOCAL_DIR="/Users/js/g9/nba_data/odds_report_engine"

echo "=========================================="
echo "Deploying Odds Report Engine to VPS"
echo "=========================================="

# Step 1: Copy Python files
echo ""
echo "[1/4] Copying Python modules..."
scp "${LOCAL_DIR}/odds_api_adapter.py" "${VPS_HOST}:${VPS_DIR}/sources/"
scp "${LOCAL_DIR}/graph_odds_report_generator.py" "${VPS_HOST}:${VPS_DIR}/"
scp "${LOCAL_DIR}/test_local.py" "${VPS_HOST}:${VPS_DIR}/test_vps.py"

# Step 2: Create reports directory on VPS
echo ""
echo "[2/4] Creating reports directory..."
ssh ${VPS_HOST} "mkdir -p ${VPS_DIR}/odds_reports"

# Step 3: Install Python dependencies
echo ""
echo "[3/4] Installing dependencies..."
ssh ${VPS_HOST} << 'EOF'
cd /opt/g9/nba-collector

# Install required packages
pip3 install --upgrade anthropic neo4j requests

echo "✓ Dependencies installed"
EOF

# Step 4: Test deployment
echo ""
echo "[4/4] Testing deployment..."
ssh ${VPS_HOST} << 'EOF'
cd /opt/g9/nba-collector

# Check if odds_api_adapter exists
if [ -f "sources/odds_api_adapter.py" ]; then
    echo "✓ odds_api_adapter.py deployed"
else
    echo "✗ odds_api_adapter.py missing"
    exit 1
fi

# Check if report generator exists
if [ -f "graph_odds_report_generator.py" ]; then
    echo "✓ graph_odds_report_generator.py deployed"
else
    echo "✗ graph_odds_report_generator.py missing"
    exit 1
fi

# Test odds API (if key is set)
if [ -n "$ODDS_API_KEY" ]; then
    echo ""
    echo "Testing Odds API..."
    python3 sources/odds_api_adapter.py $ODDS_API_KEY
else
    echo "⚠ ODDS_API_KEY not set in environment"
fi
EOF

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH into VPS: ssh ${VPS_HOST}"
echo "2. Set API keys:"
echo "   export ODDS_API_KEY='your_key'"
echo "   export ANTHROPIC_API_KEY='your_key'"
echo "   export NEO4J_PASSWORD='your_password'"
echo ""
echo "3. Test single game:"
echo "   cd ${VPS_DIR}"
echo "   python3 graph_odds_report_generator.py --home LAL --away GSW --neo4j-password \$NEO4J_PASSWORD"
echo ""
echo "4. Generate daily reports:"
echo "   python3 graph_odds_report_generator.py --daily --neo4j-password \$NEO4J_PASSWORD"
echo ""
