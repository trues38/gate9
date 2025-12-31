# OpenRouter로 Grok 4.1 Fast 사용하기

**장점:** xAI 직접 API 대신 OpenRouter 통합 키 하나로 여러 모델 사용

---

## 🔑 OpenRouter API 키 발급

1. **OpenRouter 가입**
   - https://openrouter.ai/
   - Sign up (무료)

2. **API 키 생성**
   - Settings → API Keys
   - Create Key
   - 복사: `sk-or-v1-...`

3. **크레딧 충전**
   - Billing → Add Credits
   - $10-20 추천 (약 1-2개월 운영 가능)

---

## 💰 가격 비교

### Grok 4.1 Fast (OpenRouter)
- **Input:** $2 / 1M tokens
- **Output:** $10 / 1M tokens

### 일일 비용 계산
```
트윗당 평균:
  Input:  500 tokens (트윗 + 프롬프트)
  Output: 200 tokens (JSON 구조화)

일일 50개 트윗:
  Input:  50 × 500 = 25,000 tokens = $0.05
  Output: 50 × 200 = 10,000 tokens = $0.10
  합계: $0.15/일

월 비용: $0.15 × 30 = $4.5/월
```

**xAI 직접 대비:** 거의 동일하거나 저렴 + 관리 편의성 ↑

---

## 🔧 n8n 워크플로우 수정

### HTTP Request (Grok) 노드 변경

**기존 (xAI 직접):**
```json
{
  "url": "https://api.x.ai/v1/chat/completions",
  "authentication": "headerAuth",
  "headers": {
    "Authorization": "Bearer YOUR_XAI_API_KEY"
  }
}
```

**변경 (OpenRouter):**
```json
{
  "url": "https://openrouter.ai/api/v1/chat/completions",
  "authentication": "headerAuth",
  "headers": {
    "Authorization": "Bearer YOUR_OPENROUTER_API_KEY",
    "HTTP-Referer": "https://github.com/yourusername/g9",
    "X-Title": "G9 Economic Event Pipeline"
  }
}
```

### Request Body (동일)

```json
{
  "model": "x-ai/grok-2-1212",
  "messages": [
    {
      "role": "system",
      "content": "당신은 경제 이벤트 분류 전문가입니다..."
    },
    {
      "role": "user",
      "content": "트윗: {{ $json.text }}\n\n위 트윗을 분석하여..."
    }
  ],
  "temperature": 0.1,
  "max_tokens": 1000
}
```

### 모델 선택 옵션

OpenRouter에서 사용 가능한 Grok 모델:

1. **`x-ai/grok-2-1212`** (최신, 추천)
   - Grok 2 (2024년 12월)
   - 가격: $2 / $10 (input/output)

2. **`x-ai/grok-beta`**
   - Grok Beta
   - 가격: 비슷

3. **대안: `anthropic/claude-3-haiku`**
   - 더 저렴: $0.25 / $1.25
   - 성능: 경제 이벤트 분류 충분
   - 추천: 비용 절감 시

---

## 📝 n8n 노드 업데이트 가이드

### 1. HTTP Request 노드 클릭

### 2. URL 변경
```
https://openrouter.ai/api/v1/chat/completions
```

### 3. Authentication 설정
- Type: **Header Auth**
- Name: `Authorization`
- Value: `Bearer sk-or-v1-YOUR_KEY_HERE`

### 4. Headers 추가
**Add Header:**
- Name: `HTTP-Referer`
- Value: `https://github.com/yourusername/g9`

**Add Header:**
- Name: `X-Title`
- Value: `G9 Economic Event Pipeline`

> **참고:** OpenRouter는 HTTP-Referer와 X-Title을 권장합니다 (통계 및 크레딧 추적용)

### 5. Body (JSON) 수정
```json
{
  "model": "x-ai/grok-2-1212",
  "messages": {{ $json.messages }},
  "temperature": 0.1,
  "max_tokens": 1000
}
```

### 6. Save & Test

---

## ✅ 검증 방법

### OpenRouter API 테스트

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_OPENROUTER_KEY" \
  -H "HTTP-Referer: https://github.com/yourusername/g9" \
  -H "X-Title: G9 Test" \
  -d '{
    "model": "x-ai/grok-2-1212",
    "messages": [
      {
        "role": "user",
        "content": "Fed raises interest rates by 0.25%. Classify this economic event."
      }
    ],
    "temperature": 0.1,
    "max_tokens": 200
  }'
```

**예상 응답:**
```json
{
  "id": "gen-...",
  "model": "x-ai/grok-2-1212",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "{\"event_type\": \"PolicyChange\", \"title\": \"Fed 금리 0.25%p 인상\", ...}"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 120,
    "total_tokens": 165
  }
}
```

---

## 💡 OpenRouter 추가 기능

### 1. 모델 비교 (A/B Testing)
```json
{
  "models": [
    "x-ai/grok-2-1212",
    "anthropic/claude-3-haiku"
  ],
  "route": "fallback"
}
```
→ Grok 실패 시 Haiku로 자동 전환

### 2. 비용 모니터링
- OpenRouter Dashboard에서 실시간 확인
- 모델별 사용량 통계
- 일일/월별 크레딧 소모량

### 3. Rate Limit 자동 관리
- OpenRouter가 provider rate limit 처리
- 자동 재시도 (exponential backoff)

---

## 🔄 기존 워크플로우 마이그레이션

### 단계별 전환

1. **OpenRouter API 키 발급** (5분)
   - https://openrouter.ai/keys
   - $10 충전

2. **n8n 워크플로우 백업** (1분)
   ```bash
   cp /Users/js/g9/n8n_workflows/economic_event_pipeline.json \
      /Users/js/g9/n8n_workflows/economic_event_pipeline_xai_backup.json
   ```

3. **HTTP Request 노드 수정** (3분)
   - URL 변경
   - Authorization 헤더 교체
   - HTTP-Referer, X-Title 추가

4. **모델명 확인** (1분)
   - `x-ai/grok-2-1212` 또는 `x-ai/grok-beta`

5. **테스트 실행** (2분)
   - n8n "Test Workflow"
   - 응답 확인

6. **검증** (3분)
   ```bash
   python3 /Users/js/g9/scripts/validate_event_pipeline.py
   ```

**총 소요 시간:** 15분

---

## 📊 모델 비교 (경제 이벤트 분류)

### Grok 2 (x-ai/grok-2-1212)
- **강점:** X/Twitter 데이터 학습, 실시간 뉴스 이해
- **가격:** $2 / $10
- **추천:** 고품질 이벤트 분류 원할 때

### Claude 3 Haiku (anthropic/claude-3-haiku)
- **강점:** 저렴, 빠름, 구조화 작업 우수
- **가격:** $0.25 / $1.25 (Grok 대비 1/8)
- **추천:** 비용 절감 우선 시

### 실전 전략
```json
{
  "model": "x-ai/grok-2-1212",
  "fallback": "anthropic/claude-3-haiku"
}
```
→ 평소 Grok 사용, rate limit 시 Haiku로 전환 (비용 최적화)

---

## 🚨 주의사항

### 1. API 키 관리
- OpenRouter 키는 xAI 키와 다름
- 환경변수 설정 권장:
  ```bash
  export OPENROUTER_API_KEY="sk-or-v1-..."
  ```

### 2. Rate Limit
- OpenRouter Free Tier: 일일 한도 있음
- 크레딧 충전 후 한도 해제
- n8n Schedule: 5분 간격 권장 (트래픽 분산)

### 3. 모델 버전
- `x-ai/grok-2-1212`: 2024년 12월 버전
- 최신 버전은 OpenRouter 문서 확인
- https://openrouter.ai/models

---

## 📞 관련 자료

- **OpenRouter 문서:** https://openrouter.ai/docs
- **모델 목록:** https://openrouter.ai/models
- **가격 비교:** https://openrouter.ai/models?pricing=true
- **API Playground:** https://openrouter.ai/playground

---

## ✅ 최종 체크리스트

- [ ] OpenRouter 가입 및 API 키 발급
- [ ] $10 크레딧 충전
- [ ] n8n HTTP Request 노드 URL 변경
- [ ] Authorization 헤더 업데이트
- [ ] HTTP-Referer, X-Title 추가
- [ ] 모델명 `x-ai/grok-2-1212` 확인
- [ ] Test Workflow 실행 성공
- [ ] Event 노드 Neo4j 생성 확인
- [ ] 비용 모니터링 대시보드 확인

---

**장점 요약:**
- ✅ API 키 하나로 여러 모델 사용
- ✅ 자동 fallback (Grok → Haiku)
- ✅ 비용 대시보드 (실시간 모니터링)
- ✅ Rate limit 자동 관리
- ✅ xAI 직접 연동과 가격 동일

**추천:** OpenRouter 사용 (관리 편의성 ↑)

---

**최종 업데이트:** 2025-12-25
**작성자:** Claude Sonnet 4.5
