#!/bin/bash
#
# /opt/g9 위치로 NBA Collector 업데이트
#

set -e

VPS_IP="141.164.35.214"
VPS_USER="root"
REMOTE_DIR="/opt/g9"

echo "======================================================================"
echo "G9 NBA Collector 업데이트 → /opt/g9"
echo "======================================================================"
echo ""

# 1. 로컬에서 압축
echo "[1/4] 로컬 파일 압축 중..."
cd /Users/js/g9/vultr-g9-deploy
tar czf nba-collector-update.tar.gz nba-collector/
echo "✅ 압축 완료"
echo ""

# 2. VPS로 전송
echo "[2/4] VPS로 파일 전송 중 (비밀번호 입력)..."
scp nba-collector-update.tar.gz $VPS_USER@$VPS_IP:/tmp/
echo "✅ 전송 완료"
echo ""

# 3. VPS에서 업데이트
echo "[3/4] VPS에서 업데이트 중 (비밀번호 다시 입력)..."
ssh $VPS_USER@$VPS_IP << 'REMOTE'
    set -e

    echo "압축 해제 중..."
    cd /tmp
    tar xzf nba-collector-update.tar.gz

    echo "기존 버전 백업 중..."
    cd /opt/g9
    if [ -d "nba-collector" ]; then
        mv nba-collector nba-collector.backup.$(date +%Y%m%d_%H%M%S)
        echo "✅ 백업 완료"
    fi

    echo "새 버전 복사 중..."
    mv /tmp/nba-collector /opt/g9/

    echo "컨테이너 재시작 중..."
    cd /opt/g9
    docker compose stop nba-collector || true
    docker compose rm -f nba-collector || true
    docker compose up -d --build nba-collector

    echo ""
    echo "대기 중 (서비스 시작)..."
    sleep 5

    echo ""
    echo "컨테이너 상태:"
    docker compose ps | grep nba-collector

    echo ""
    echo "로그 (최근 30줄):"
    docker compose logs --tail 30 nba-collector
REMOTE

echo ""
echo "[4/4] 헬스체크..."
sleep 3

# 4. 헬스체크
ssh $VPS_USER@$VPS_IP "curl -s http://localhost:8001/health" && {
    echo ""
    echo ""
    echo "======================================================================"
    echo "✅ 업데이트 완료!"
    echo "======================================================================"
    echo ""
    echo "새 버전 확인:"
    ssh $VPS_USER@$VPS_IP "curl -s http://localhost:8001/health"
    echo ""
    echo ""
    echo "API 엔드포인트:"
    echo "  - Health:  http://$VPS_IP:8001/health"
    echo "  - Budget:  http://$VPS_IP:8001/budget/status"
    echo "  - Storage: http://$VPS_IP:8001/storage/stats"
    echo ""
} || {
    echo ""
    echo "⚠️  서비스 응답 없음"
    echo "로그 확인: ssh $VPS_USER@$VPS_IP 'cd /opt/g9 && docker-compose logs nba-collector'"
}

# 로컬 임시 파일 삭제
rm -f nba-collector-update.tar.gz
echo "✅ 로컬 임시 파일 정리 완료"
