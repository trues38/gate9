#!/bin/bash
# BTC Macro Engine Runner
#
# Usage:
#   ./run_monitor.sh              # 1회 Law 체크
#   ./run_monitor.sh decision     # 투입 결정 게이트
#   ./run_monitor.sh meta         # META-LAYER 상태
#   ./run_monitor.sh service      # SaaS 서비스 (daemon + 알림)
#   ./run_monitor.sh notify-test  # 알림 테스트
#
# VPS Deployment:
#   ./deploy/setup-vps.sh         # systemd 설치
#   ./deploy/setup-docker.sh      # Docker 설치

cd "$(dirname "$0")"

# Python 환경 설정
export PYTHONPATH=src

# Python 경로 자동 감지
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif command -v python3.11 &> /dev/null; then
    PYTHON="python3.11"
elif [ -f "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
else
    PYTHON="python3"
fi

# .env 파일 로드
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

case "$1" in
    decision)
        # Human-in-the-loop decision gate
        $PYTHON src/btc_engine/meta/decision_gate.py
        ;;
    meta)
        # Full META-LAYER status
        $PYTHON src/btc_engine/meta/law_health_monitor.py
        ;;
    service)
        # SaaS service daemon mode
        echo "[$(date)] Starting BTC Macro Service..."
        $PYTHON src/btc_engine/service.py --daemon
        ;;
    notify-test)
        # Test notifications
        $PYTHON src/btc_engine/service.py --test
        ;;
    daily-report)
        # Send daily report
        $PYTHON src/btc_engine/service.py --daily-report
        ;;
    test)
        # Legacy: test alert (console only)
        $PYTHON src/btc_engine/alerts/etf_law_monitor.py --test
        ;;
    force)
        # Force check even if already alerted today
        $PYTHON src/btc_engine/alerts/etf_law_monitor.py --force
        ;;
    *)
        # Default: single Law check
        echo "[$(date)] Checking ETF Law..."
        $PYTHON src/btc_engine/alerts/etf_law_monitor.py
        ;;
esac
