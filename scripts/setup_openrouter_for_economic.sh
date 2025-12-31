#!/bin/bash
# 경제 이벤트 파이프라인용 OpenRouter 설정
# NBA 프로젝트와 동일한 API 키 사용

set -e

echo "════════════════════════════════════════════════════════════════"
echo "경제 이벤트 파이프라인 - OpenRouter 설정"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 1. 환경변수 확인
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY 환경변수가 설정되지 않았습니다."
    echo ""
    echo "설정 방법:"
    echo "  export OPENROUTER_API_KEY='sk-or-v1-...'"
    echo ""
    echo "또는 ~/.bashrc 또는 ~/.zshrc에 추가:"
    echo "  echo 'export OPENROUTER_API_KEY=\"sk-or-v1-...\"' >> ~/.zshrc"
    echo ""
    echo "API Key 발급: https://openrouter.ai/keys"
    echo ""
    exit 1
else
    echo "✓ OPENROUTER_API_KEY 발견"
    KEY_PREFIX="${OPENROUTER_API_KEY:0:15}"
    echo "  ${KEY_PREFIX}..."
    echo ""
fi

# 2. API 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "OpenRouter API 연결 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
  https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "HTTP-Referer: https://github.com/g9-economic-regime" \
  -H "X-Title: G9 Economic Event Pipeline" \
  -d '{
    "model": "x-ai/grok-2-1212",
    "messages": [
      {"role": "user", "content": "Fed raises interest rates by 0.25%. Classify this economic event in JSON format."}
    ],
    "temperature": 0.1,
    "max_tokens": 200
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ API 연결 성공 (HTTP 200)"
    echo ""
    echo "응답 샘플:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
else
    echo "❌ API 연결 실패 (HTTP $HTTP_CODE)"
    echo ""
    echo "응답:"
    echo "$BODY"
    echo ""
    exit 1
fi

# 3. n8n 환경변수 설정 가이드
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "n8n 환경변수 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if command -v docker &> /dev/null; then
    echo "Docker가 설치되어 있습니다."
    echo ""
    echo "n8n Docker 컨테이너에 환경변수 전달:"
    echo ""
    echo "  docker run -d --name n8n \\"
    echo "    -p 5678:5678 \\"
    echo "    -e OPENROUTER_API_KEY=\"\$OPENROUTER_API_KEY\" \\"
    echo "    -v ~/.n8n:/home/node/.n8n \\"
    echo "    n8nio/n8n"
    echo ""

    # n8n 컨테이너 확인
    if docker ps -a | grep -q n8n; then
        echo "기존 n8n 컨테이너 발견:"
        docker ps -a | grep n8n
        echo ""
        echo "환경변수 업데이트 방법:"
        echo "  1. 컨테이너 재시작:"
        echo "     docker stop n8n"
        echo "     docker rm n8n"
        echo "     # 위 docker run 명령 실행"
        echo ""
        echo "  2. 또는 n8n 웹UI에서 Credentials 직접 입력"
    fi
else
    echo "n8n이 로컬로 설치된 경우:"
    echo "  환경변수가 이미 전달됩니다."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "n8n 워크플로우 노드 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "HTTP Request (Grok Analysis) 노드:"
echo ""
echo "  URL: https://openrouter.ai/api/v1/chat/completions"
echo ""
echo "  Headers:"
echo "    Authorization: Bearer \$OPENROUTER_API_KEY"
echo "    Content-Type: application/json"
echo "    HTTP-Referer: https://github.com/g9-economic-regime"
echo "    X-Title: G9 Economic Event Pipeline"
echo ""
echo "  Model: x-ai/grok-2-1212"
echo ""

# 4. 비용 추정
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "예상 비용"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Grok 2 (x-ai/grok-2-1212):"
echo "  Input:  \$2 / 1M tokens"
echo "  Output: \$10 / 1M tokens"
echo ""
echo "경제 이벤트 파이프라인 (일일 50개 트윗):"
echo "  Input:  50 × 500 tokens = 25,000 tokens = \$0.05/일"
echo "  Output: 50 × 200 tokens = 10,000 tokens = \$0.10/일"
echo "  합계: \$0.15/일 = \$4.50/월"
echo ""
echo "NBA 파이프라인과 합산:"
echo "  NBA: \$0.50/월 (경기일만 사용)"
echo "  경제: \$4.50/월 (매일 사용)"
echo "  총 비용: ~\$5/월"
echo ""

# 5. 다음 단계
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 설정 완료 - 다음 단계"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. n8n 워크플로우 임포트"
echo "   - http://localhost:5678"
echo "   - Import from File"
echo "   - /Users/js/g9/n8n_workflows/economic_event_pipeline.json"
echo ""
echo "2. HTTP Request 노드 수정"
echo "   - URL: https://openrouter.ai/api/v1/chat/completions"
echo "   - Model: x-ai/grok-2-1212"
echo "   - Headers 업데이트 (위 참고)"
echo ""
echo "3. Test Workflow 실행"
echo ""
echo "4. 검증"
echo "   python3 /Users/js/g9/scripts/validate_event_pipeline.py"
echo ""
echo "════════════════════════════════════════════════════════════════"
