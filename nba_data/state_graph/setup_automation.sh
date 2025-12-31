#!/bin/bash

# NBA Data Automation Setup Script
# 자동화 파이프라인 설정

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"

echo "========================================================================"
echo "NBA Data Automation Setup"
echo "========================================================================"
echo ""

# 1. 로그 디렉토리 생성
echo "[1/3] Setting up log directory..."
mkdir -p "$SCRIPT_DIR/.automation_logs"
echo "✅ Log directory created"
echo ""

# 2. 자동화 권한 설정
echo "[2/3] Setting up automation permissions..."
chmod +x "$SCRIPT_DIR/daily_automation.py"
echo "✅ Permissions set"
echo ""

# 3. Cron 작업 설정
echo "[3/3] Setting up cron job..."

# 현재 crontab 확인
CRON_JOB="0 9 * * * cd $PROJECT_DIR && $VENV_PYTHON $SCRIPT_DIR/daily_automation.py"

# crontab에 이미 존재하는지 확인
if crontab -l 2>/dev/null | grep -q "daily_automation.py"; then
    echo "⚠️  Cron job already exists"
else
    # 새 cron 작업 추가
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added"
fi

echo ""
echo "========================================================================"
echo "Automation Setup Complete"
echo "========================================================================"
echo ""
echo "📅 Schedule: Daily at 09:00 UTC (18:00 KST)"
echo "📂 Logs: $SCRIPT_DIR/.automation_logs/"
echo ""
echo "To verify the cron job:"
echo "  crontab -l"
echo ""
echo "To view logs:"
echo "  tail -f $SCRIPT_DIR/.automation_logs/automation_\$(date +%Y-%m-%d).log"
echo ""
