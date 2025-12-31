#!/bin/bash
# VPS Neo4j SSH 터널 시작 (비밀번호 입력 필요)

echo "🔌 VPS Neo4j SSH 터널 시작..."
echo ""
echo "VPS: 141.164.35.214"
echo "포트 포워딩:"
echo "  로컬 7687 → VPS Neo4j 7687"
echo "  로컬 7474 → VPS Neo4j Browser 7474"
echo ""
echo "⚠️ VPS root 비밀번호를 입력하세요:"
echo ""

# SSH 터널 시작 (포그라운드로 - 비밀번호 입력 가능)
ssh -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214

# 또는 백그라운드로 실행하려면:
# ssh -f -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214
