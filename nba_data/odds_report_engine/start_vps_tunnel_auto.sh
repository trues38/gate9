#!/bin/bash
# VPS Neo4j SSH 터널 자동 시작 (SSH 키 등록 후 사용)

echo "🔌 VPS Neo4j SSH 터널 자동 연결 중..."
echo ""

# 기존 터널 종료
if [ -f /tmp/neo4j_ssh_tunnel.pid ]; then
    OLD_PID=$(cat /tmp/neo4j_ssh_tunnel.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️ 기존 터널 종료 중 (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 1
    fi
fi

# SSH 터널 시작 (백그라운드)
ssh -f -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214

# PID 찾기
sleep 1
NEW_PID=$(pgrep -f "ssh -f -L 7687")

if [ -n "$NEW_PID" ]; then
    echo $NEW_PID > /tmp/neo4j_ssh_tunnel.pid

    echo "✅ SSH 터널 연결 완료!"
    echo "   PID: $NEW_PID"
    echo ""
    echo "📊 로컬에서 VPS Neo4j 연결:"
    echo "   bolt://localhost:7687"
    echo "   Username: neo4j"
    echo "   Password: test123"
    echo ""
    echo "🌐 Neo4j Browser:"
    echo "   http://localhost:7474"
    echo ""
    echo "🛑 터널 종료:"
    echo "   kill $NEW_PID"
    echo "   또는: pkill -f 'ssh -f -L 7687'"
    echo ""

    # 연결 테스트
    echo "🔍 연결 테스트 중..."
    python3 << 'EOF'
from neo4j import GraphDatabase
import sys

try:
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test123"))
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as total")
        total = result.single()["total"]
        print(f"✅ VPS Neo4j 연결 성공!")
        print(f"   총 노드: {total:,}개")
    driver.close()
except Exception as e:
    print(f"❌ 연결 실패: {e}")
    sys.exit(1)
EOF

else
    echo "❌ SSH 터널 시작 실패"
    echo ""
    echo "SSH 키가 등록되지 않았을 수 있습니다."
    echo "먼저 실행하세요:"
    echo "  ./setup_ssh_key.sh"
    echo ""
    echo "또는 수동으로:"
    echo "  ./start_vps_tunnel.sh"
    exit 1
fi
