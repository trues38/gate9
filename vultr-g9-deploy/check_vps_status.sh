#!/bin/bash
#
# VPS 상태 원격 확인 스크립트
#

VPS_IP="141.164.35.214"

echo "======================================================================"
echo "G9 VPS 상태 확인"
echo "======================================================================"
echo ""

echo "🏥 [1/5] 헬스체크..."
curl -s http://$VPS_IP:8001/health | python3 -m json.tool 2>/dev/null || curl -s http://$VPS_IP:8001/health
echo ""
echo ""

echo "💰 [2/5] API 예산 상태..."
curl -s http://$VPS_IP:8001/budget/status | python3 -m json.tool 2>/dev/null || curl -s http://$VPS_IP:8001/budget/status
echo ""
echo ""

echo "💾 [3/5] 저장소 통계..."
curl -s http://$VPS_IP:8001/storage/stats | python3 -m json.tool 2>/dev/null || curl -s http://$VPS_IP:8001/storage/stats
echo ""
echo ""

echo "🐳 [4/5] Docker 컨테이너 상태..."
ssh root@$VPS_IP "docker compose -f /opt/g9/docker-compose.yml ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null || {
    echo "SSH 접속 필요 (비밀번호 입력)"
    ssh root@$VPS_IP "docker ps --format 'table {{.Names}}\t{{.Status}}'"
}
echo ""

echo "📊 [5/5] 시스템 리소스..."
ssh root@$VPS_IP "echo 'Memory:' && free -h | grep Mem && echo '' && echo 'Disk:' && df -h / | grep -v Filesystem" 2>/dev/null || {
    echo "SSH 접속 필요 (비밀번호 입력)"
}
echo ""

echo "======================================================================"
echo "✅ 확인 완료!"
echo "======================================================================"
echo ""
echo "웹 인터페이스:"
echo "  - NBA Collector API: http://$VPS_IP:8001/health"
echo "  - Neo4j Browser:     http://$VPS_IP:7474"
echo "  - N8N Workflows:     http://$VPS_IP:5678"
echo ""
