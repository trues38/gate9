# n8n 워크플로우: xAI → OpenRouter 마이그레이션

**소요 시간:** 5분
**난이도:** 쉬움

---

## 🎯 변경 사항 요약

### 변경 전 (xAI 직접)
```
URL: https://api.x.ai/v1/chat/completions
인증: xAI API Key
모델: x-ai/grok-4.1-fast
```

### 변경 후 (OpenRouter)
```
URL: https://openrouter.ai/api/v1/chat/completions
인증: OpenRouter API Key
모델: x-ai/grok-2-1212
fallback: anthropic/claude-3-haiku (선택)
```

---

## 📝 단계별 가이드

### 1. OpenRouter API 키 발급
```
1. https://openrouter.ai/ 접속
2. Sign up (무료)
3. Settings → API Keys → Create Key
4. 복사: sk-or-v1-xxxxxxxxxx
5. Billing → Add Credits ($10 추천)
```

### 2. n8n 워크플로우 열기
```
http://localhost:5678
→ Workflows
→ "Economic Event Pipeline" 클릭
```

### 3. "Grok Analysis" 노드 수정

#### A. URL 변경
```
기존: https://api.x.ai/v1/chat/completions
변경: https://openrouter.ai/api/v1/chat/completions
```

#### B. Headers 업데이트

**기존 Headers:**
```json
{
  "Authorization": "Bearer {{ $credentials.xaiApiKey }}",
  "Content-Type": "application/json"
}
```

**변경된 Headers:**
```json
{
  "Authorization": "Bearer YOUR_OPENROUTER_API_KEY",
  "Content-Type": "application/json",
  "HTTP-Referer": "https://github.com/g9-economic-regime",
  "X-Title": "G9 Economic Event Pipeline"
}
```

**n8n에서 설정:**
1. **Header 1:**
   - Name: `Authorization`
   - Value: `Bearer sk-or-v1-YOUR_KEY_HERE`

2. **Header 2:**
   - Name: `Content-Type`
   - Value: `application/json`

3. **Header 3 (추가):**
   - Name: `HTTP-Referer`
   - Value: `https://github.com/g9-economic-regime`

4. **Header 4 (추가):**
   - Name: `X-Title`
   - Value: `G9 Economic Event Pipeline`

#### C. Body (JSON) 수정

**모델명만 변경:**
```json
{
  "model": "x-ai/grok-2-1212",  // 변경됨
  "messages": [...],
  "temperature": 0.1,
  "max_tokens": 1000
}
```

**또는 Fallback 추가 (권장):**
```json
{
  "model": "x-ai/grok-2-1212",
  "models": ["x-ai/grok-2-1212", "anthropic/claude-3-haiku"],
  "route": "fallback",
  "messages": [...],
  "temperature": 0.1,
  "max_tokens": 1000
}
```

### 4. Save & Test
```
1. 노드 우측 상단 "Save" 클릭
2. 워크플로우 "Test Workflow" 클릭
3. 결과 확인:
   ✓ Grok Analysis 노드 성공 (200 OK)
   ✓ Parse Grok Response 노드 JSON 파싱
   ✓ Neo4j 노드 Event 생성
```

---

## 🔧 복사-붙여넣기 코드

### Headers (n8n Code Node)

**Authorization:**
```
Bearer sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE
```

**HTTP-Referer:**
```
https://github.com/g9-economic-regime
```

**X-Title:**
```
G9 Economic Event Pipeline
```

### Body (n8n JSON)

```json
{
  "model": "x-ai/grok-2-1212",
  "messages": [
    {
      "role": "system",
      "content": "당신은 경제 이벤트 분류 전문가입니다.\n\n입력: X 트윗\n출력: JSON 형식의 구조화된 Event\n\n규칙:\n1. 시장 영향력 판단 (significant: true/false)\n2. Event 타입 분류 (PolicyChange, EconomicData, GeopoliticalEvent, SentimentShift, MarketShock)\n3. magnitude 추출 (25bp = 0.25, 2.5% = 2.5, $85B = 85)\n4. direction 판단 (up, down, neutral)\n5. affected_factors 추론 ([\"금리\", \"유동성\", \"심리\", \"달러\"] 중 선택)\n6. confidence 계산 (0-1, Tier 1 = 0.9+, Tier 2 = 0.7+, Tier 3 = 0.5+)\n\n출력 형식:\n{\n  \"significant\": boolean,\n  \"type\": string,\n  \"subtype\": string,\n  \"magnitude\": number | null,\n  \"direction\": \"up\" | \"down\" | \"neutral\",\n  \"affected_factors\": string[],\n  \"confidence\": number,\n  \"title\": string,\n  \"description\": string,\n  \"keywords\": string[]\n}\n\nsignificant가 false면 다른 필드는 생략 가능."
    },
    {
      "role": "user",
      "content": "출처: {{ $json.source_account }} (Tier {{ $json.source_tier }})\n트윗: {{ $json.text }}\n시간: {{ $json.created_at }}"
    }
  ],
  "temperature": 0.1,
  "max_tokens": 1000,
  "route": "fallback",
  "models": ["x-ai/grok-2-1212", "anthropic/claude-3-haiku"]
}
```

---

## ✅ 검증 방법

### 1. curl 테스트
```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_OPENROUTER_KEY" \
  -H "HTTP-Referer: https://github.com/g9-economic-regime" \
  -H "X-Title: G9 Test" \
  -d '{
    "model": "x-ai/grok-2-1212",
    "messages": [
      {"role": "user", "content": "Fed raises rates 0.25%. Classify this."}
    ],
    "temperature": 0.1,
    "max_tokens": 200
  }'
```

**예상 응답:**
```json
{
  "id": "gen-xxx",
  "model": "x-ai/grok-2-1212",
  "choices": [{
    "message": {
      "content": "{\"significant\": true, \"type\": \"PolicyChange\", ...}"
    }
  }]
}
```

### 2. n8n 워크플로우 테스트
```
1. n8n → "Economic Event Pipeline"
2. "Test Workflow" 클릭
3. 각 노드 결과 확인:
   ✓ Twitter Monitor: 트윗 수집
   ✓ Keyword Filter: 통과
   ✓ Whitelist Check: Tier 할당
   ✓ Grok Analysis: 200 OK
   ✓ Parse Grok Response: JSON 객체
   ✓ Neo4j: Event 노드 생성
```

### 3. Neo4j 검증
```cypher
// Neo4j Browser (http://localhost:7475)
MATCH (e:Event)
WHERE e.created_at > datetime() - duration('PT1H')
RETURN e.title, e.type, e.confidence
ORDER BY e.created_at DESC
LIMIT 5;
```

---

## 💰 비용 비교

### 일일 50개 트윗 처리 시

**xAI 직접:**
- Input: 25,000 tokens × $2 / 1M = $0.05
- Output: 10,000 tokens × $10 / 1M = $0.10
- **합계: $0.15/일 = $4.50/월**

**OpenRouter (Grok 2):**
- Input: 25,000 tokens × $2 / 1M = $0.05
- Output: 10,000 tokens × $10 / 1M = $0.10
- **합계: $0.15/일 = $4.50/월**

**OpenRouter (Grok → Haiku fallback):**
- Grok: 40개 × $0.15 = $6.00
- Haiku: 10개 × $0.015 = $0.15
- **합계: $6.15/월 (fallback 활용 시)**

**OpenRouter (Haiku만 사용):**
- Input: 25,000 tokens × $0.25 / 1M = $0.006
- Output: 10,000 tokens × $1.25 / 1M = $0.013
- **합계: $0.019/일 = $0.57/월 (1/8 비용!)**

---

## 💡 추천 전략

### Option 1: Grok만 사용 (고품질)
```json
{
  "model": "x-ai/grok-2-1212"
}
```
- **장점:** 최고 품질 (X 데이터 학습)
- **비용:** $4.50/월

### Option 2: Grok → Haiku Fallback (균형)
```json
{
  "models": ["x-ai/grok-2-1212", "anthropic/claude-3-haiku"],
  "route": "fallback"
}
```
- **장점:** 안정성 + 비용 절감
- **비용:** $4-6/월 (rate limit 시 Haiku)

### Option 3: Haiku만 사용 (저비용)
```json
{
  "model": "anthropic/claude-3-haiku"
}
```
- **장점:** 극저비용
- **비용:** $0.57/월
- **단점:** 경제 이벤트 분류 품질 약간 낮음

---

## 🔄 롤백 방법

문제 발생 시 xAI 직접 연동으로 복원:

```bash
# 백업 워크플로우 복원
cp /Users/js/g9/n8n_workflows/economic_event_pipeline_xai_backup.json \
   /Users/js/g9/n8n_workflows/economic_event_pipeline.json

# n8n에서 재임포트
```

또는 수동으로:
1. URL: `https://api.x.ai/v1/chat/completions`
2. Headers: `Authorization: Bearer {{ xAI_KEY }}`
3. Model: `x-ai/grok-4.1-fast`

---

## 📊 OpenRouter 대시보드

마이그레이션 후 모니터링:

1. **비용 추적**
   - https://openrouter.ai/activity
   - 모델별 사용량 실시간 확인

2. **Rate Limit 모니터링**
   - Generation 탭에서 fallback 발생 확인
   - Grok → Haiku 전환 빈도

3. **응답 시간**
   - Grok: ~2-3초
   - Haiku: ~1-2초

---

## ✅ 마이그레이션 체크리스트

- [ ] OpenRouter API 키 발급
- [ ] $10 크레딧 충전
- [ ] n8n 워크플로우 백업
- [ ] URL 변경 (openrouter.ai)
- [ ] Headers 업데이트 (4개)
- [ ] Model 변경 (grok-2-1212)
- [ ] Fallback 설정 (선택)
- [ ] Test Workflow 실행
- [ ] Event 노드 생성 확인
- [ ] OpenRouter 대시보드 비용 확인

---

**예상 소요 시간:** 5분
**난이도:** ★☆☆☆☆

**장점:**
- ✅ API 키 하나로 여러 모델
- ✅ 자동 fallback (안정성 ↑)
- ✅ 비용 대시보드
- ✅ Rate limit 자동 관리
- ✅ 가격 동일 or 저렴

---

**최종 업데이트:** 2025-12-25
**작성자:** Claude Sonnet 4.5
