#!/bin/bash
set -e

echo "🚀 n8n NBA 실시간 파이프라인 배포"
echo "=================================="
echo ""

# 1. 환경변수 파일 확인
if [ ! -f .env.n8n ]; then
    echo "⚠️  .env.n8n 파일이 없습니다."
    echo ""
    echo "다음 명령으로 생성하세요:"
    echo "  cp .env.n8n.example .env.n8n"
    echo "  vim .env.n8n  # API Keys 입력"
    echo ""
    exit 1
fi

echo "✅ 환경변수 파일 확인"

# 2. 기존 Neo4j 컨테이너 확인
if ! docker ps | grep -q "neo4j-nba"; then
    echo "❌ neo4j-nba 컨테이너가 실행 중이 아닙니다."
    echo ""
    echo "Neo4j를 먼저 시작하세요:"
    echo "  docker start neo4j-nba"
    echo ""
    exit 1
fi

echo "✅ Neo4j 컨테이너 실행 확인 (neo4j-nba)"

# 3. nba-network 생성 (없으면)
if ! docker network ls | grep -q "nba-network"; then
    echo "📡 nba-network 생성 중..."
    docker network create nba-network
    echo "✅ nba-network 생성 완료"
else
    echo "✅ nba-network 이미 존재"
fi

# 4. Neo4j 컨테이너를 nba-network에 연결
if ! docker network inspect nba-network | grep -q "neo4j-nba"; then
    echo "🔗 neo4j-nba를 nba-network에 연결 중..."
    docker network connect nba-network neo4j-nba
    echo "✅ Neo4j 네트워크 연결 완료"
else
    echo "✅ Neo4j 이미 nba-network에 연결됨"
fi

# 5. n8n 워크플로우 디렉토리 생성
mkdir -p n8n_workflows

# 6. n8n 컨테이너 시작
echo ""
echo "🐳 n8n 컨테이너 시작 중..."
docker-compose -f docker-compose-n8n.yml --env-file .env.n8n up -d

# 7. 헬스체크 대기
echo ""
echo "⏳ n8n 시작 대기 중 (최대 60초)..."
for i in {1..60}; do
    if docker exec n8n-nba wget --spider -q http://localhost:5678/healthz 2>/dev/null; then
        echo "✅ n8n 정상 시작 완료!"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# 8. 접속 정보 출력
echo ""
echo "=================================="
echo "✅ 배포 완료!"
echo "=================================="
echo ""
echo "📌 n8n 웹 UI:"
echo "   http://localhost:5678"
echo ""
echo "📌 로그인 정보:"
source .env.n8n
echo "   Username: ${N8N_USER}"
echo "   Password: ${N8N_PASSWORD}"
echo ""
echo "📌 Neo4j 연결 정보:"
echo "   URI: bolt://neo4j-nba:7687"
echo "   Username: ${NEO4J_USERNAME}"
echo ""
echo "📌 다음 단계:"
echo "   1. http://localhost:5678 접속"
echo "   2. n8n_nba_realtime_workflow.json Import"
echo "   3. Credentials 설정 (Neo4j, OpenRouter, Telegram)"
echo "   4. Workflow 활성화"
echo ""
echo "📌 Neo4j 연결 테스트:"
echo "   python3 test_neo4j_connection.py"
echo ""
