#!/bin/bash
# Interactive SSH Tunnel - 비밀번호 입력 가능

echo "🔌 VPS Neo4j SSH 터널 (Interactive)"
echo "=" * 70
echo ""
echo "VPS 비밀번호를 입력해주세요:"
echo ""

# 기존 터널 정리
pkill -f "ssh.*7687.*141.164.35.214" 2>/dev/null

# Interactive SSH 터널 (foreground, 비밀번호 입력 가능)
ssh -L 7687:localhost:7687 -L 7474:localhost:7474 root@141.164.35.214 -N

# 여기는 터널이 종료되면 실행됨
echo ""
echo "✅ 터널이 종료되었습니다"
