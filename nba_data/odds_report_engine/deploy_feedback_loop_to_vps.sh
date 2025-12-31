#!/bin/bash
# Feedback Loop 시스템 VPS 배포 스크립트

VPS_HOST="141.164.35.214"
VPS_USER="root"
VPS_DIR="/opt/g9/nba-feedback-loop"
LOCAL_DIR="/Users/js/g9/nba_data/odds_report_engine"

echo "🚀 Feedback Loop 시스템 VPS 배포"
echo "=" * 70
echo ""
echo "VPS: $VPS_USER@$VPS_HOST"
echo "배포 위치: $VPS_DIR"
echo ""

# 1. VPS 디렉토리 생성
echo "[1/5] VPS 디렉토리 생성..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $VPS_DIR"

# 2. 핵심 파일 업로드
echo "[2/5] 파일 업로드 중..."

# Feedback Loop 스키마
scp $LOCAL_DIR/FEEDBACK_LOOP_SCHEMA.cypher $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/FEEDBACK_LOOP_QUERIES.cypher $VPS_USER@$VPS_HOST:$VPS_DIR/

# Python 파이프라인
scp $LOCAL_DIR/raw_data_pipeline.py $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/feedback_loop_example.py $VPS_USER@$VPS_HOST:$VPS_DIR/

# 문서
scp $LOCAL_DIR/FEEDBACK_LOOP_SYSTEM.md $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/DATA_STORAGE_PIPELINE.md $VPS_USER@$VPS_HOST:$VPS_DIR/

echo "  ✅ 파일 업로드 완료"

# 3. Neo4j 스키마 적용
echo "[3/5] Neo4j 스키마 적용 중..."

ssh $VPS_USER@$VPS_HOST << 'EOFSSH'
cd /opt/g9/nba-feedback-loop

# Neo4j 컨테이너 확인
if docker ps | grep -q neo4j; then
    echo "  ✅ Neo4j 실행 중"

    # 스키마 적용
    docker exec -i $(docker ps | grep neo4j | awk '{print $1}') \
        cypher-shell -u neo4j -p nba_vultr_2025 < FEEDBACK_LOOP_SCHEMA.cypher

    echo "  ✅ 스키마 적용 완료"
else
    echo "  ⚠️ Neo4j 컨테이너가 실행 중이 아닙니다"
    echo "     먼저 Neo4j를 시작하세요:"
    echo "     docker start <neo4j-container>"
fi
EOFSSH

# 4. Python 환경 설정
echo "[4/5] Python 환경 설정..."

ssh $VPS_USER@$VPS_HOST << 'EOFSSH'
cd /opt/g9/nba-feedback-loop

# 필요한 패키지 설치
pip3 install neo4j python-dotenv requests 2>/dev/null

echo "  ✅ Python 패키지 설치 완료"
EOFSSH

# 5. .env 파일 생성
echo "[5/5] 환경 변수 설정..."

ssh $VPS_USER@$VPS_HOST << 'EOFSSH'
cd /opt/g9/nba-feedback-loop

# .env 파일 생성
cat > .env << 'ENV'
# Neo4j 연결
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=nba_vultr_2025

# Odds API
ODDS_API_KEY=b01049f1f29d61c53189799c40d66f69

# OpenRouter
OPENROUTER_API_KEY=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
ENV

echo "  ✅ .env 파일 생성 완료"
EOFSSH

# 6. 테스트 실행
echo ""
echo "=" * 70
echo "✅ 배포 완료!"
echo "=" * 70
echo ""
echo "📝 VPS에서 실행 방법:"
echo ""
echo "1. SSH 접속:"
echo "   ssh root@$VPS_HOST"
echo ""
echo "2. 디렉토리 이동:"
echo "   cd $VPS_DIR"
echo ""
echo "3. 테스트 실행:"
echo "   python3 feedback_loop_example.py"
echo ""
echo "4. 실제 파이프라인:"
echo "   python3 raw_data_pipeline.py"
echo ""
echo "📋 다음 단계:"
echo "   - n8n 워크플로우 설정 (N8N_FEEDBACK_LOOP_WORKFLOW.md 참조)"
echo "   - 경기 후 자동 실행 cron 설정"
echo ""

# 원격에서 빠른 테스트
echo "🧪 VPS에서 연결 테스트 중..."
ssh $VPS_USER@$VPS_HOST "cd $VPS_DIR && python3 -c '
from neo4j import GraphDatabase
driver = GraphDatabase.driver(\"bolt://localhost:7687\", auth=(\"neo4j\", \"nba_vultr_2025\"))
with driver.session() as session:
    result = session.run(\"MATCH (n) RETURN count(n) as total\")
    print(f\"✅ VPS Neo4j: {result.single()[\"total\"]:,}개 노드\")
driver.close()
'"

echo ""
echo "🎉 Feedback Loop 시스템 VPS 배포 완료!"
