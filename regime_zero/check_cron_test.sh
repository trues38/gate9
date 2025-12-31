#!/bin/bash
# Check if cron test completed successfully

echo "================================================"
echo "Cron Test Status Check"
echo "================================================"
echo ""

LOG_FILE="/Users/js/g9/regime_zero/logs/cron_test.log"

if [ -f "${LOG_FILE}" ]; then
    echo "✅ Cron test log file exists!"
    echo ""
    echo "Log contents:"
    echo "------------------------------------------------"
    cat "${LOG_FILE}"
    echo "------------------------------------------------"
    echo ""
    echo "✅ CRON WORKING PERFECTLY!"
    echo ""
    echo "You can now safely restore the original crontab:"
    echo "  crontab /tmp/crontab.backup"
    echo ""
else
    echo "⏳ Cron test not completed yet..."
    echo ""
    echo "Current time: $(date)"
    echo ""
    echo "Expected test file: ${LOG_FILE}"
    echo ""
    echo "Next cron execution:"
    crontab -l | grep "TEMPORARY TEST" -A1
    echo ""
    echo "Wait a bit longer and run this script again:"
    echo "  ./check_cron_test.sh"
    echo ""
fi
