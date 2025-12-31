#!/bin/bash
# Wait 70 seconds and check result

LOG_FILE="/Users/js/g9/regime_zero/logs/cron_test.log"

echo "⏳ Waiting 70 seconds for cron to execute..."
echo ""

for i in {70..1}; do
    printf "\r⏱️  %2d seconds remaining... " $i
    sleep 1

    # Check if file appeared
    if [ -f "${LOG_FILE}" ]; then
        echo ""
        echo ""
        echo "================================================"
        echo "✅ CRON EXECUTED!"
        echo "================================================"
        echo ""
        cat "${LOG_FILE}"
        echo ""
        echo "================================================"
        echo "✅ Cron is working! Restoring original crontab..."
        echo "================================================"

        # Restore original
        cat > /tmp/g9_crontab_final.txt << 'EOF'
# G9 Daily Bulletin Generation
# Runs every day at 7:00 AM KST (after US market close)
0 7 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
EOF
        crontab /tmp/g9_crontab_final.txt

        echo ""
        echo "Final crontab:"
        crontab -l
        echo ""
        echo "✅ All done! Production cron is ready for tomorrow 07:00"
        exit 0
    fi
done

echo ""
echo ""
echo "❌ Cron did not execute"
echo ""
echo "Checking for log file..."
ls -la "${LOG_FILE}" 2>&1
echo ""

echo "This might be a macOS security issue."
echo "Please check: System Preferences > Security & Privacy > Full Disk Access"
echo "Add: /usr/sbin/cron"
