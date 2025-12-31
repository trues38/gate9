#!/bin/bash
# SSH 터널 종료 스크립트

echo "🛑 SSH 터널 종료 중..."

if [ -f /tmp/neo4j_ssh_tunnel.pid ]; then
    PID=$(cat /tmp/neo4j_ssh_tunnel.pid)

    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ 터널 종료됨 (PID: $PID)"
        rm /tmp/neo4j_ssh_tunnel.pid
    else
        echo "⚠️ 터널이 이미 종료됨"
        rm /tmp/neo4j_ssh_tunnel.pid
    fi
else
    # PID 파일 없으면 프로세스 찾아서 종료
    pkill -f "ssh.*7687.*141.164.35.214"
    pkill -f "autossh.*7687.*141.164.35.214"
    echo "✅ 모든 Neo4j 터널 종료"
fi
