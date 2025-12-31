#!/bin/bash
# G9 Cron Setup Script
# 이 스크립트는 Daily Bulletin cron job을 자동으로 설정합니다.

set -e

echo "================================================"
echo "G9 Daily Bulletin - Cron Setup"
echo "================================================"
echo ""

# 현재 crontab 백업
echo "[1/5] Backing up current crontab..."
if crontab -l > /tmp/crontab.backup 2>/dev/null; then
    echo "✅ Current crontab backed up to /tmp/crontab.backup"
else
    echo "⚠️ No existing crontab found (this is OK)"
    touch /tmp/crontab.backup
fi

# 새 crontab 생성
echo ""
echo "[2/5] Creating new crontab entry..."

# 기존 crontab + 새 entry
cat /tmp/crontab.backup > /tmp/crontab.new

# G9 entry가 이미 있는지 확인
if grep -q "G9 Daily Bulletin" /tmp/crontab.backup 2>/dev/null; then
    echo "⚠️ G9 Daily Bulletin entry already exists!"
    echo ""
    echo "Current entry:"
    grep -A1 "G9 Daily Bulletin" /tmp/crontab.backup
    echo ""
    read -p "Replace with new entry? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
    # 기존 entry 제거
    grep -v "G9 Daily Bulletin" /tmp/crontab.backup | grep -v "run_daily_bulletin.sh" > /tmp/crontab.new
fi

# 새 entry 추가
cat >> /tmp/crontab.new << 'EOF'

# G9 Daily Bulletin Generation
# Runs every day at 7:00 AM KST (after US market close)
0 7 * * * /Users/js/g9/regime_zero/run_daily_bulletin.sh >> /Users/js/g9/regime_zero/logs/cron.log 2>&1
EOF

echo "✅ New crontab entry created"

# Crontab 내용 표시
echo ""
echo "[3/5] Preview new crontab:"
echo "================================================"
cat /tmp/crontab.new
echo "================================================"

# 확인
echo ""
read -p "[4/5] Install this crontab? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
fi

# Crontab 설치
crontab /tmp/crontab.new
echo "✅ Crontab installed"

# 검증
echo ""
echo "[5/5] Verifying installation..."
if crontab -l | grep -q "run_daily_bulletin.sh"; then
    echo "✅ Cron job successfully registered!"
else
    echo "❌ Verification failed"
    exit 1
fi

echo ""
echo "================================================"
echo "CRON SETUP COMPLETE!"
echo "================================================"
echo ""
echo "📅 Schedule: Every day at 7:00 AM"
echo "📂 Logs: /Users/js/g9/regime_zero/logs/cron.log"
echo "📄 Output: /Users/js/g9/regime_zero/reports/bulletins/BULLETIN_YYYY-MM-DD.md"
echo ""
echo "Next steps:"
echo "  1. Check crontab: crontab -l"
echo "  2. Monitor logs: tail -f /Users/js/g9/regime_zero/logs/cron.log"
echo "  3. Test manually: /Users/js/g9/regime_zero/run_daily_bulletin.sh"
echo ""
echo "⚠️ NOTE: On macOS, you may need to grant Terminal Full Disk Access"
echo "   System Preferences > Security & Privacy > Privacy > Full Disk Access"
echo ""
