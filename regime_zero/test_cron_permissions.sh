#!/bin/bash
# Cron Permission Test Script
# This script tests if cron has proper permissions to run

set -e

echo "================================================"
echo "Cron Permission Test"
echo "================================================"
echo ""

# Test 1: Can we write to the project directory?
echo "[Test 1] Writing to project directory..."
TEST_FILE="/Users/js/g9/regime_zero/logs/.cron_permission_test"
if echo "test" > "${TEST_FILE}" 2>/dev/null; then
    echo "✅ Can write to logs directory"
    rm -f "${TEST_FILE}"
else
    echo "❌ Cannot write to logs directory"
    exit 1
fi

# Test 2: Can we execute python3?
echo ""
echo "[Test 2] Executing Python..."
PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
if ${PYTHON} --version >/dev/null 2>&1; then
    echo "✅ Can execute Python: $(${PYTHON} --version 2>&1)"
else
    echo "❌ Cannot execute Python"
    exit 1
fi

# Test 3: Can we import required modules?
echo ""
echo "[Test 3] Importing Python modules..."
if ${PYTHON} -c "import yfinance, pandas, dotenv" 2>/dev/null; then
    echo "✅ All Python modules available"
else
    echo "❌ Missing Python modules"
    ${PYTHON} -c "import yfinance, pandas, dotenv" 2>&1
    exit 1
fi

# Test 4: Can we read .env file?
echo ""
echo "[Test 4] Reading .env file..."
if [ -f /Users/js/g9/regime_zero/.env ]; then
    if cat /Users/js/g9/regime_zero/.env >/dev/null 2>&1; then
        echo "✅ Can read .env file"
    else
        echo "❌ Cannot read .env file"
        exit 1
    fi
else
    echo "⚠️ No .env file found (may not be required)"
fi

# Test 5: Can we create bulletin?
echo ""
echo "[Test 5] Running minimal pipeline test..."
cd /Users/js/g9/regime_zero
if ${PYTHON} -c "from engine.data_validator import DataValidator; print('✅ Can import DataValidator')" 2>/dev/null; then
    echo "✅ Pipeline modules accessible"
else
    echo "❌ Cannot access pipeline modules"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ ALL TESTS PASSED"
echo "================================================"
echo ""
echo "Cron has proper permissions to run the bulletin pipeline."
echo ""
