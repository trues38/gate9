#!/bin/bash
# 매일 경기 분석 자동화 스크립트
# 사용법: ./daily_betting_report.sh

echo "================================================================================"
echo "NBA 내일 경기 베팅 분석 보고서 생성"
echo "================================================================================"
echo ""

# 작업 디렉토리로 이동
cd "$(dirname "$0")"

# Step 0: 어제 경기 결과를 Neo4j에 추가 (최신 패턴 유지)
echo "🔄 Step 0: 어제 경기 결과 업데이트 (패턴 최신화)..."
python3 update_yesterday_games.py
if [ $? -ne 0 ]; then
    echo "⚠️  어제 경기 업데이트 실패 (계속 진행)"
fi
echo ""

# Step 1: 내일 경기 스케줄 가져오기
echo "📅 Step 1: 내일 경기 스케줄 가져오기..."
python3 fetch_tomorrow_games.py
if [ $? -ne 0 ]; then
    echo "❌ 스케줄 가져오기 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# Step 2: ESPN 프리뷰 정보 수집
echo "💰 Step 2: ESPN 프리뷰 정보 수집..."
python3 fetch_game_preview.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 프리뷰 수집 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# Step 3: 경기 컨텍스트 계산
echo "📋 Step 3: 경기 컨텍스트 계산 (휴식일, 부상자, 백투백)..."
python3 calculate_game_context.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 컨텍스트 계산 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# Step 4: 컨텍스트 기반 패턴 분석
echo "🎯 Step 4: 과거 패턴 기반 예측 생성..."
python3 context_based_analysis.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 패턴 분석 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# Step 5: 최근 트렌드 분석
echo "🔥 Step 5: 최근 트렌드 분석 (폼/연승/득점)..."
python3 recent_form_analysis.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 트렌드 분석 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# Step 6: 통합 보고서 생성
echo "📊 Step 6: 최종 통합 보고서 생성..."
python3 analyze_with_preview.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 보고서 생성 실패"
    exit 1
fi
echo "✅ 완료"
echo ""

# 생성된 파일 확인
echo "================================================================================"
echo "✅ 베팅 분석 보고서 생성 완료!"
echo "================================================================================"
echo ""
echo "📁 생성된 파일:"
ls -lh context_based_analysis_*.txt 2>/dev/null | tail -1 | awk '{print "  🎯 패턴 분석: " $9 " (" $5 ")"}'
ls -lh recent_trends_*.txt 2>/dev/null | tail -1 | awk '{print "  🔥 트렌드 분석: " $9 " (" $5 ")"}'
ls -lh enhanced_analysis_*.txt 2>/dev/null | tail -1 | awk '{print "  📊 통합 보고서: " $9 " (" $5 ")"}'
echo ""

# 최신 파일 경로
CONTEXT_FILE=$(ls -t context_based_analysis_*.txt 2>/dev/null | head -1)
TRENDS_FILE=$(ls -t recent_trends_*.txt 2>/dev/null | head -1)
ENHANCED_FILE=$(ls -t enhanced_analysis_*.txt 2>/dev/null | head -1)

echo "💡 보고서 확인:"
echo "  cat $CONTEXT_FILE   # 역사적 패턴 (휴식일, 백투백)"
echo "  cat $TRENDS_FILE    # 최근 트렌드 (폼, 연승)"
echo "  cat $ENHANCED_FILE  # 통합 (ESPN + 패턴)"
echo ""

echo "📌 권장 사항:"
echo "  • 경기 시작 4-6시간 전에 다시 실행 (심판 정보 업데이트)"
echo "  • 부상자 명단은 경기 직전까지 변동 가능"
echo ""
