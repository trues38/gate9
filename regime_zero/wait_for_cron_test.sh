#!/bin/bash
# Wait for Cron Test and Display Results

LOG_FILE="/Users/js/g9/regime_zero/logs/cron_test.log"
MONITOR_LOG="/Users/js/g9/regime_zero/logs/permission_test_monitor.log"

echo "================================================"
echo "Cron Test Monitor - Waiting for execution..."
echo "================================================"
echo ""
echo "Current time: $(date +%H:%M:%S)"
echo "Expected execution: 22:16:00"
echo ""
echo "Checking every 10 seconds..."
echo ""

# Wait loop
MAX_WAIT=600  # 10 minutes
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if [ -f "${LOG_FILE}" ]; then
        echo ""
        echo "================================================"
        echo "✅ CRON TEST EXECUTED!"
        echo "================================================"
        echo ""
        echo "Test log contents:"
        echo "------------------------------------------------"
        cat "${LOG_FILE}"
        echo "------------------------------------------------"
        echo ""

        # Update monitor log
        echo "" >> "${MONITOR_LOG}"
        echo "-----------------------------------------------------------------" >> "${MONITOR_LOG}"
        echo "[$(date +%H:%M)] 실시간 Cron 테스트 완료" >> "${MONITOR_LOG}"
        echo "-----------------------------------------------------------------" >> "${MONITOR_LOG}"
        echo "" >> "${MONITOR_LOG}"
        cat "${LOG_FILE}" >> "${MONITOR_LOG}"
        echo "" >> "${MONITOR_LOG}"
        echo "상태: ✅ 테스트 성공" >> "${MONITOR_LOG}"
        echo "" >> "${MONITOR_LOG}"
        echo "=================================================================" >> "${MONITOR_LOG}"
        echo "최종 결론: Cron 완전 작동. Production 준비 완료." >> "${MONITOR_LOG}"
        echo "=================================================================" >> "${MONITOR_LOG}"

        echo "✅ Monitor log updated: ${MONITOR_LOG}"
        echo ""
        echo "Next steps:"
        echo "  1. Restore original crontab: crontab /tmp/crontab.backup"
        echo "  2. Verify: crontab -l"
        echo ""
        exit 0
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo "⏳ Still waiting... (${ELAPSED}s elapsed)"
done

echo ""
echo "❌ Timeout reached (${MAX_WAIT}s)"
echo ""
echo "Test log not created. Possible issues:"
echo "  1. Cron permissions problem"
echo "  2. Script execution error"
echo ""
echo "Check system logs:"
echo "  log show --predicate 'eventMessage contains \"cron\"' --last 10m"
echo ""

# Update monitor log with failure
echo "" >> "${MONITOR_LOG}"
echo "-----------------------------------------------------------------" >> "${MONITOR_LOG}"
echo "[$(date +%H:%M)] 실시간 Cron 테스트 타임아웃" >> "${MONITOR_LOG}"
echo "-----------------------------------------------------------------" >> "${MONITOR_LOG}"
echo "" >> "${MONITOR_LOG}"
echo "상태: ❌ 테스트 실패 (타임아웃)" >> "${MONITOR_LOG}"
echo "" >> "${MONITOR_LOG}"

exit 1
