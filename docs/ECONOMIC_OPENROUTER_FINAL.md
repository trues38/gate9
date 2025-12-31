# 경제 이벤트 파이프라인 - OpenRouter 최종 설정 가이드

**NBA 프로젝트와 동일한 API 키 사용**

---

## ✅ 발견 사항

NBA 실시간 파이프라인에서 이미 OpenRouter 사용 중:
- **위치:** `/Users/js/g9/nba_data/state_graph/`
- **모델:** `x-ai/grok-4.1-fast` (Grok 4.1 Fast)
- **용도:** 라인업 변경, 부상 리포트 정규화
- **API 키:** 환경변수 `OPENROUTER_API_KEY`

**결론:** 동일한 API 키를 경제 파이프라인에서 재사용하면 즉시 사용 가능!

---

## 🚀 빠른 시작 (3단계)

### 1. 환경변수 확인

```bash
# API 키 확인
echo $OPENROUTER_API_KEY

# 없으면 설정
export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"

# 영구 설정 (선택)
echo 'export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"' >> ~/.zshrc
source ~/.zshrc
```

### 2. API 테스트

```bash
# 자동 설정 스크립트 실행
bash /Users/js/g9/scripts/setup_openrouter_for_economic.sh

# 예상 출력:
# ✅ API 연결 성공 (HTTP 200)
# ✅ 환경변수 설정 확인
# ✅ n8n 노드 설정 가이드
```

### 3. n8n 워크플로우 수정

#### A. URL 변경
```
기존: https://api.x.ai/v1/chat/completions
변경: https://openrouter.ai/api/v1/chat/completions
```

#### B. Headers 업데이트
```
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json
HTTP-Referer: https://github.com/g9-economic-regime
X-Title: G9 Economic Event Pipeline
```

#### C. Model 변경
```json
{
  "model": "x-ai/grok-2-1212",  // 최신 Grok 2
  "messages": [...],
  "temperature": 0.1,
  "max_tokens": 1000
}
```

---

## 📊 NBA vs 경제 파이프라인 비교

| 항목 | NBA | 경제 |
|------|-----|------|
| **모델** | x-ai/grok-4.1-fast | x-ai/grok-2-1212 |
| **용도** | 라인업/부상 정규화 | 경제 이벤트 분류 |
| **일일 트윗** | 10-20개 (경기일만) | 50-100개 (매일) |
| **월 비용** | $0.50 | $4.50 |
| **API 키** | OPENROUTER_API_KEY | OPENROUTER_API_KEY (동일) |

**통합 비용:** ~$5/월 (두 파이프라인 합산)

---

## 🔧 n8n HTTP Request 노드 설정

### 완전한 설정 (복사-붙여넣기)

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://openrouter.ai/api/v1/chat/completions",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "Bearer {{ $env.OPENROUTER_API_KEY }}"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        },
        {
          "name": "HTTP-Referer",
          "value": "https://github.com/g9-economic-regime"
        },
        {
          "name": "X-Title",
          "value": "G9 Economic Event Pipeline"
        }
      ]
    },
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={\n  \"model\": \"x-ai/grok-2-1212\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"당신은 경제 이벤트 분류 전문가입니다.\\n\\n입력: X 트윗\\n출력: JSON 형식의 구조화된 Event\\n\\n규칙:\\n1. 시장 영향력 판단 (significant: true/false)\\n2. Event 타입 분류 (PolicyChange, EconomicData, GeopoliticalEvent, SentimentShift, MarketShock)\\n3. magnitude 추출 (25bp = 0.25, 2.5% = 2.5, $85B = 85)\\n4. direction 판단 (up, down, neutral)\\n5. affected_factors 추론 ([\\\"금리\\\", \\\"유동성\\\", \\\"심리\\\", \\\"달러\\\"] 중 선택)\\n6. confidence 계산 (0-1, Tier 1 = 0.9+, Tier 2 = 0.7+, Tier 3 = 0.5+)\\n\\n출력 형식:\\n{\\n  \\\"significant\\\": boolean,\\n  \\\"type\\\": string,\\n  \\\"subtype\\\": string,\\n  \\\"magnitude\\\": number | null,\\n  \\\"direction\\\": \\\"up\\\" | \\\"down\\\" | \\\"neutral\\\",\\n  \\\"affected_factors\\\": string[],\\n  \\\"confidence\\\": number,\\n  \\\"title\\\": string,\\n  \\\"description\\\": string,\\n  \\\"keywords\\\": string[]\\n}\\n\\nsignificant가 false면 다른 필드는 생략 가능.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"출처: {{ $json.source_account }} (Tier {{ $json.source_tier }})\\n트윗: {{ $json.text }}\\n시간: {{ $json.created_at }}\"\n    }\n  ],\n  \"temperature\": 0.1,\n  \"max_tokens\": 1000,\n  \"route\": \"fallback\",\n  \"models\": [\"x-ai/grok-2-1212\", \"anthropic/claude-3-haiku\"]\n}",
    "options": {}
  },
  "name": "Grok Analysis (OpenRouter)",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.1
}
```

---

## 🎯 NBA 프로젝트 설정 재사용

### 이미 구축된 인프라

1. **OpenRouter 계정**
   - 크레딧 잔액 확인: https://openrouter.ai/credits
   - 필요시 $10 추가 충전 (경제 + NBA 통합 운영)

2. **환경변수 설정**
   ```bash
   # NBA 프로젝트에서 이미 설정됨
   cat ~/.zshrc | grep OPENROUTER
   ```

3. **테스트 스크립트**
   ```bash
   # NBA 테스트 스크립트 참고
   cat /Users/js/g9/nba_data/state_graph/test_grok_openrouter.py

   # 경제용으로 수정 (선택)
   # 동일한 API 패턴 사용 가능
   ```

---

## ✅ 검증 절차

### 1. 환경변수 확인
```bash
bash /Users/js/g9/scripts/setup_openrouter_for_economic.sh
```

**예상 출력:**
```
✓ OPENROUTER_API_KEY 발견
  sk-or-v1-xxxxx...

✅ API 연결 성공 (HTTP 200)

응답 샘플:
{
  "id": "gen-xxx",
  "model": "x-ai/grok-2-1212",
  "choices": [...]
}
```

### 2. n8n 워크플로우 테스트
```
1. http://localhost:5678 접속
2. "Economic Event Pipeline" 워크플로우 열기
3. "Grok Analysis" 노드 클릭
4. URL 및 Headers 업데이트
5. "Test Workflow" 실행
6. 결과 확인:
   ✓ Grok Analysis: 200 OK
   ✓ Parse Grok Response: JSON 파싱
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

## 💰 통합 비용 관리

### OpenRouter 대시보드
- **URL:** https://openrouter.ai/activity
- **확인 항목:**
  - NBA 파이프라인 사용량
  - 경제 파이프라인 사용량
  - 통합 월 비용
  - 모델별 비율

### 예상 통합 비용
```
NBA 파이프라인:
  - 경기일만 작동 (주 3-4일)
  - 일일 10-20개 트윗
  - 월 $0.50

경제 파이프라인:
  - 매일 작동 (24/7)
  - 일일 50-100개 트윗
  - 월 $4.50

총 비용: $5/월
→ $5-10 크레딧 충전으로 1-2개월 운영
```

---

## 🔄 NBA → 경제 적용 사례

### NBA 프로젝트에서 배운 패턴

1. **정규화 프롬프트 설계**
   ```python
   # NBA: 라인업 변경
   "OUT|RULED OUT|INACTIVE" → "OUT"

   # 경제: 금리 변경
   "hawkish|rate hike|increase" → "PolicyChange"
   ```

2. **신뢰도 점수 계산**
   ```python
   # NBA: Tier 기반
   OfficialNBARefs = 0.95
   ShamsCharania = 0.90

   # 경제: Tier 기반
   Fed = 0.95
   Bloomberg = 0.85
   ```

3. **JSON 파싱 강화**
   ```python
   # 코드 블록 제거 (NBA 스크립트에서 검증됨)
   if "```json" in content:
       content = content.split("```json")[1].split("```")[0].strip()
   ```

---

## 📚 참고 자료

### NBA 프로젝트 문서
- OpenRouter 설정: `/Users/js/g9/nba_data/state_graph/GROK_OPENROUTER_SETUP.md`
- 테스트 스크립트: `/Users/js/g9/nba_data/state_graph/test_grok_openrouter.py`
- n8n 워크플로우: `/Users/js/g9/nba_data/state_graph/n8n_nba_realtime_workflow.json`

### 경제 프로젝트 문서
- 파이프라인 설계: `/Users/js/g9/docs/REALTIME_ECONOMIC_EVENT_PIPELINE.md`
- n8n 워크플로우: `/Users/js/g9/n8n_workflows/economic_event_pipeline.json`
- 검증 스크립트: `/Users/js/g9/scripts/validate_event_pipeline.py`

### OpenRouter
- 대시보드: https://openrouter.ai/activity
- 모델 목록: https://openrouter.ai/models
- API 문서: https://openrouter.ai/docs

---

## 🎁 즉시 실행 가능

**모든 준비 완료:**
- ✅ OpenRouter API 키 (NBA에서 재사용)
- ✅ 환경변수 설정
- ✅ 테스트 스크립트
- ✅ n8n 노드 설정 코드
- ✅ 검증 절차

**배포 시작:**
```bash
# 1. 환경 확인
bash /Users/js/g9/scripts/setup_openrouter_for_economic.sh

# 2. n8n에서 워크플로우 수정
#    - URL: openrouter.ai
#    - Model: grok-2-1212
#    - Headers 업데이트

# 3. 검증
python3 /Users/js/g9/scripts/validate_event_pipeline.py

# 4. 운영 시작
# n8n에서 "Active" 토글 ON
```

**예상 소요 시간:** 10분

---

**최종 업데이트:** 2025-12-25
**작성자:** Claude Sonnet 4.5
**프로젝트:** G9 경제 레짐 분석 시스템
