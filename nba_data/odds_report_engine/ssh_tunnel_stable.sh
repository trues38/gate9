#!/bin/bash
# SSH 터널 안정화 스크립트 (autossh 방식)
# 끊기면 자동 재연결

echo "🔌 VPS Neo4j SSH 터널 - 안정화 버전"
echo "=" * 70

# autossh 설치 확인
if ! command -v autossh &> /dev/null; then
    echo "⚠️ autossh가 설치되어 있지 않습니다."
    echo ""
    echo "설치 방법:"
    echo "  macOS: brew install autossh"
    echo "  Linux: sudo apt install autossh"
    echo ""
    read -p "지금 설치하시겠습니까? (y/n): " install_choice

    if [ "$install_choice" = "y" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install autossh
        else
            sudo apt install -y autossh
        fi
    else
        echo "일반 ssh로 진행합니다..."
        USE_AUTOSSH=false
    fi
else
    USE_AUTOSSH=true
fi

# 기존 터널 종료
echo ""
echo "🧹 기존 터널 정리 중..."
pkill -f "ssh.*7687.*141.164.35.214" 2>/dev/null
pkill -f "autossh.*7687.*141.164.35.214" 2>/dev/null
sleep 2

# VPS 정보
VPS_HOST="141.164.35.214"
VPS_USER="root"
LOCAL_PORT_NEO4J=7687
LOCAL_PORT_BROWSER=7474
REMOTE_PORT_NEO4J=7687
REMOTE_PORT_BROWSER=7474

# PID 파일
PID_FILE="/tmp/neo4j_ssh_tunnel.pid"

echo ""
echo "📡 터널 설정:"
echo "  VPS: $VPS_USER@$VPS_HOST"
echo "  로컬 7687 → VPS Neo4j 7687"
echo "  로컬 7474 → VPS Neo4j Browser 7474"
echo ""

if [ "$USE_AUTOSSH" = true ]; then
    echo "🚀 autossh로 안정화된 터널 시작..."
    echo "   (끊기면 자동 재연결)"
    echo ""

    # autossh 실행
    # -M 0: 모니터링 포트 비활성화 (SSH 자체 KeepAlive 사용)
    # -f: 백그라운드 실행
    # -N: 명령 실행 안 함 (터널만)
    # ServerAliveInterval 30: 30초마다 생존 신호
    # ServerAliveCountMax 3: 3번 실패하면 재연결

    autossh -M 0 -f -N \
        -o "ServerAliveInterval 30" \
        -o "ServerAliveCountMax 3" \
        -o "ExitOnForwardFailure yes" \
        -L ${LOCAL_PORT_NEO4J}:localhost:${REMOTE_PORT_NEO4J} \
        -L ${LOCAL_PORT_BROWSER}:localhost:${REMOTE_PORT_BROWSER} \
        ${VPS_USER}@${VPS_HOST}

    # PID 찾기
    sleep 2
    TUNNEL_PID=$(pgrep -f "autossh.*7687.*$VPS_HOST")

else
    echo "🔌 일반 SSH 터널 시작..."
    echo "   (수동 재연결 필요)"
    echo ""

    # 일반 SSH (백그라운드)
    ssh -f -N \
        -o "ServerAliveInterval 30" \
        -o "ServerAliveCountMax 3" \
        -L ${LOCAL_PORT_NEO4J}:localhost:${REMOTE_PORT_NEO4J} \
        -L ${LOCAL_PORT_BROWSER}:localhost:${REMOTE_PORT_BROWSER} \
        ${VPS_USER}@${VPS_HOST}

    # PID 찾기
    sleep 2
    TUNNEL_PID=$(pgrep -f "ssh.*7687.*$VPS_HOST" | head -1)
fi

# 결과 확인
if [ -n "$TUNNEL_PID" ]; then
    echo $TUNNEL_PID > $PID_FILE

    echo "✅ SSH 터널 연결 성공!"
    echo "   PID: $TUNNEL_PID"
    echo ""
    echo "📊 로컬에서 VPS Neo4j 사용:"
    echo "   bolt://localhost:7687"
    echo "   Username: neo4j"
    echo "   Password: nba_vultr_2025"
    echo ""
    echo "🌐 Neo4j Browser:"
    echo "   http://localhost:7474"
    echo ""
    echo "🔍 터널 상태 확인:"
    echo "   ps -p $TUNNEL_PID"
    echo ""
    echo "🛑 터널 종료:"
    echo "   kill $TUNNEL_PID"
    echo "   또는: ./stop_tunnel.sh"
    echo ""

    # 연결 테스트
    echo "🧪 연결 테스트 중..."
    sleep 2

    python3 << 'PYTEST'
from neo4j import GraphDatabase
import sys

try:
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "nba_vultr_2025")
    )

    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as total")
        total = result.single()["total"]
        print(f"✅ VPS Neo4j 연결 성공!")
        print(f"   총 노드: {total:,}개")

    driver.close()

except Exception as e:
    print(f"❌ 연결 실패: {e}")
    sys.exit(1)
PYTEST

    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 모든 준비 완료!"
        if [ "$USE_AUTOSSH" = true ]; then
            echo "   autossh가 터널을 자동 관리합니다."
            echo "   네트워크가 끊겨도 자동 재연결됩니다."
        fi
    else
        echo ""
        echo "⚠️ 터널은 생성되었으나 Neo4j 연결 실패"
        echo "   VPS Neo4j가 실행 중인지 확인하세요:"
        echo "   ssh root@$VPS_HOST 'docker ps | grep neo4j'"
    fi

else
    echo "❌ SSH 터널 시작 실패"
    echo ""
    echo "가능한 원인:"
    echo "  1. VPS SSH 연결 문제 (비밀번호/키 확인)"
    echo "  2. 포트 7687이 이미 사용 중"
    echo "  3. 방화벽 차단"
    echo ""
    echo "수동 디버깅:"
    echo "  ssh -v root@$VPS_HOST"
    exit 1
fi
