#!/bin/bash
#
# VPS에 /tweets/recent endpoint 배포
#

set -e

VPS_IP="141.164.35.214"
VPS_USER="root"
VPS_PATH="/opt/g9/nba-collector"

echo "========================================================================"
echo "🚀 VPS에 /tweets/recent endpoint 배포"
echo "========================================================================"
echo ""
echo "대상 VPS: $VPS_USER@$VPS_IP"
echo "경로: $VPS_PATH"
echo ""

# 1. 파일 복사
echo "[1/3] raw_storage.py 복사 중..."
scp domains/nba/collector/storage/raw_storage.py $VPS_USER@$VPS_IP:$VPS_PATH/storage/raw_storage.py

echo ""
echo "[2/3] app_api.py 복사 중..."
scp domains/nba/collector/app_api.py $VPS_USER@$VPS_IP:$VPS_PATH/app_api.py

echo ""
echo "[3/3] nba-collector 컨테이너 재시작 중..."
ssh $VPS_USER@$VPS_IP "cd /opt/g9 && docker compose restart nba-collector"

echo ""
echo "✅ 배포 완료!"
echo ""
echo "========================================================================"
echo "🧪 테스트 명령어:"
echo "========================================================================"
echo ""
echo "# 최근 트윗 확인"
echo "curl \"http://$VPS_IP:8001/tweets/recent?domain=nba&limit=5\" | python3 -m json.tool"
echo ""
