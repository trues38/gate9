#!/bin/bash
set -e

echo "🧹 n8n 정리 스크립트"
echo "=================================="
echo ""

# 옵션 파싱
REMOVE_DATA=false
if [ "$1" == "--full" ]; then
    REMOVE_DATA=true
    echo "⚠️  전체 정리 모드: 볼륨 데이터까지 삭제됩니다."
    echo ""
fi

# 1. n8n 컨테이너 중지 및 삭제
echo "🛑 n8n 컨테이너 중지 중..."
docker-compose -f docker-compose-n8n.yml down

echo "✅ n8n 컨테이너 중지 완료"

# 2. neo4j-nba를 nba-network에서 분리
if docker network inspect nba-network | grep -q "neo4j-nba" 2>/dev/null; then
    echo "🔌 neo4j-nba를 nba-network에서 분리 중..."
    docker network disconnect nba-network neo4j-nba || true
    echo "✅ 네트워크 분리 완료"
fi

# 3. nba-network 삭제 (n8n만 사용하는 네트워크)
if docker network ls | grep -q "nba-network"; then
    echo "📡 nba-network 삭제 중..."
    docker network rm nba-network || true
    echo "✅ 네트워크 삭제 완료"
fi

# 4. 볼륨 데이터 삭제 (선택)
if [ "$REMOVE_DATA" = true ]; then
    echo ""
    echo "⚠️  n8n 데이터 볼륨을 삭제합니다..."
    read -p "정말 삭제하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume rm n8n_nba_data || true
        echo "✅ 볼륨 삭제 완료"
    else
        echo "❌ 볼륨 삭제 취소"
    fi
fi

echo ""
echo "=================================="
echo "✅ 정리 완료!"
echo "=================================="
echo ""
echo "📌 상태:"
echo "   - n8n 컨테이너: 삭제됨"
echo "   - nba-network: 삭제됨"
echo "   - neo4j-nba: 영향 없음 (계속 실행 중)"

if [ "$REMOVE_DATA" = true ]; then
    echo "   - n8n 데이터: 삭제됨 (워크플로우 포함)"
else
    echo "   - n8n 데이터: 보존됨 (재배포 시 복구 가능)"
fi

echo ""
echo "📌 재배포:"
echo "   ./deploy_n8n.sh"
echo ""
