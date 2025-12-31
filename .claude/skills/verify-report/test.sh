#!/bin/bash
# verify-report 스킬 테스트

echo "🔍 verify-report 스킬 테스트"
echo "================================"
echo ""

# Neo4j 비밀번호 확인
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "⚠️  NEO4J_PASSWORD 환경 변수가 설정되지 않았습니다"
    echo "   export NEO4J_PASSWORD='your_password'"
    exit 1
fi

# 테스트 보고서 선택
REPORT="/Users/js/g9/nba_data/odds_reports/graphrag_DET_at_LAL_OPUS45_REWRITE.md"

if [ ! -f "$REPORT" ]; then
    echo "❌ 테스트 보고서를 찾을 수 없습니다: $REPORT"
    exit 1
fi

echo "📄 테스트 보고서: $(basename $REPORT)"
echo ""

# 스킬 실행
cd /Users/js/g9/.claude/skills/verify-report
python3 main.py "$REPORT"

exit_code=$?

echo ""
echo "================================"
if [ $exit_code -eq 0 ]; then
    echo "✅ 테스트 성공 (점수 80+)"
else
    echo "⚠️  테스트 실패 (점수 < 80 또는 오류)"
fi
