# API 키 발급 및 설정 가이드

**생성일:** 2025-12-26
**프로젝트:** 경제 이벤트 파이프라인

---

## 1. Twitter API (X API)

### 발급 방법:

1. **Twitter Developer Portal 접속**
   - URL: https://developer.twitter.com/en/portal/dashboard
   - 기존 Twitter 계정으로 로그인

2. **App 생성**
   - "Create Project" → "Create App"
   - App Name: `Economic Event Monitor` (아무거나)
   - Use Case: Research/Analysis 선택

3. **API Keys 생성**
   - App 설정에서 "Keys and Tokens" 탭
   - **"Bearer Token"** 생성 (Read-only 권한)
   - ⚠️ 토큰 복사 후 안전하게 보관

### n8n 설정:

**노드:** `Twitter Monitor`

1. 노드 클릭 → Credential 선택
2. **Authentication:** OAuth 2.0
3. **Access Token:** `[Your Bearer Token]`
4. Save

### 비용:

- **Free Tier:** 월 500,000 트윗 읽기 (충분함)
- 초과 시: $100/월 (Basic Tier)

### 테스트:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.twitter.com/2/tweets/search/recent?query=from:federalreserve&max_results=10"
```

---

## 2. xAI Grok API (추천)

### 발급 방법:

1. **xAI Console 접속**
   - URL: https://console.x.ai/
   - X 계정으로 로그인

2. **API Key 생성**
   - Dashboard → "API Keys"
   - "Create new secret key"
   - Key 복사 (다시 볼 수 없음!)

3. **크레딧 충전**
   - Billing → Add Credits
   - 최소 $25 (테스트용 충분)

### n8n 설정:

**노드:** `HTTP Request (Grok Analysis)`

1. 노드 클릭
2. **Authentication:** Generic Credential Type → Header Auth
3. Header Name: `Authorization`
4. Header Value: `Bearer YOUR_XAI_API_KEY`
5. Save

### 비용 예상:

**모델:** `grok-2-1212` (최신)
- Input: $2 / 1M tokens
- Output: $10 / 1M tokens
- 트윗당 평균: ~$0.005 (500 토큰 가정)
- **월 비용 (1일 100트윗):** ~$15

### 테스트:

```bash
curl -X POST https://api.x.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "grok-2-1212",
    "temperature": 0
  }'
```

---

## 3. OpenRouter (Grok 대안 - 더 저렴)

### 발급 방법:

1. **OpenRouter 가입**
   - URL: https://openrouter.ai/
   - Google/GitHub 계정으로 간편 가입

2. **API Key 생성**
   - Settings → API Keys
   - "Create Key"
   - Key 복사

3. **크레딧 충전**
   - Billing → Add Credits
   - 최소 $10 (테스트용)

### n8n 설정:

**노드:** `HTTP Request (Grok Analysis)` 수정

1. **URL 변경:**
   ```
   https://openrouter.ai/api/v1/chat/completions
   ```

2. **Headers 추가:**
   ```
   Authorization: Bearer YOUR_OPENROUTER_KEY
   HTTP-Referer: http://localhost:5678
   X-Title: Economic Event Pipeline
   ```

3. **Body 수정 (모델 변경):**
   ```json
   {
     "model": "x-ai/grok-2-1212",
     "messages": [...]
   }
   ```

### 비용 (OpenRouter):

**Grok 2 via OpenRouter:**
- Input: $2 / 1M tokens
- Output: $10 / 1M tokens
- xAI 직접 사용과 동일

**더 저렴한 대안:**
- `google/gemini-pro-1.5`: $0.125 / 1M (거의 무료)
- `anthropic/claude-3-haiku`: $0.25 / 1M

### 테스트:

```bash
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "HTTP-Referer: http://localhost" \
  -d '{
    "model": "x-ai/grok-2-1212",
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

---

## 4. Slack Webhook (선택사항)

### 발급 방법:

1. **Slack Workspace 접속**
   - 알림 받을 워크스페이스

2. **Incoming Webhook 앱 추가**
   - https://api.slack.com/apps
   - "Create New App" → "From scratch"
   - App Name: `Economic Alerts`

3. **Webhook URL 생성**
   - Features → Incoming Webhooks
   - Activate Incoming Webhooks: ON
   - "Add New Webhook to Workspace"
   - 채널 선택: `#economic-alerts` (새로 만들기)
   - Webhook URL 복사

### n8n 설정:

**노드:** `Slack High Confidence`

1. 노드 클릭
2. **Webhook URL:** `[복사한 URL]`
3. **Channel:** `#economic-alerts`
4. Save

### 테스트:

```bash
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{"text":"🚨 Test Alert from Economic Pipeline"}'
```

---

## 우선순위 (API 키 발급 순서)

### 즉시 필요:
1. ✅ **Neo4j** - 이미 준비됨
2. 🟡 **Grok/OpenRouter** - 핵심 분석 엔진

### 나중에 추가 가능:
3. 🟢 **Twitter API** - 없으면 수동 테스트 가능
4. ⚪ **Slack** - 알림용, 선택사항

---

## 빠른 시작 (최소 구성)

**테스트만 해보려면:**

1. **Neo4j 설정** (완료)
2. **OpenRouter 가입** ($10 충전)
   - 가장 빠르고 저렴
   - Grok/Gemini/Claude 모두 사용 가능
3. **Twitter는 건너뛰기**
   - n8n에서 수동으로 테스트 데이터 입력

**비용:** $10 (100-200회 분석 가능)

---

## 보안 주의사항

### API 키 보관:

```bash
# 환경변수로 관리 (권장)
export XAI_API_KEY="sk-..."
export OPENROUTER_KEY="sk-..."
export TWITTER_TOKEN="AAA..."

# .bashrc 또는 .zshrc에 추가
echo 'export XAI_API_KEY="sk-..."' >> ~/.zshrc
```

### Git에 절대 커밋하지 말 것:

```bash
# .gitignore 확인
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

### n8n 크레덴셜:

- n8n은 자동으로 암호화하여 `~/.n8n/database.sqlite`에 저장
- 백업 시 주의 (평문 노출 가능)

---

## 문제 해결

### Twitter API 403 Forbidden:
- Bearer Token 권한 확인 (Read-only 충분)
- App이 Suspended 되지 않았는지 확인

### Grok API 401 Unauthorized:
- API Key 앞에 "Bearer " 포함 확인
- Key 만료 여부 확인 (xAI Console)

### OpenRouter 429 Rate Limit:
- 무료 티어 제한 (분당 20 요청)
- 크레딧 충전하면 제한 완화

### Neo4j Connection Refused:
```bash
# Docker 컨테이너 재시작
docker restart neo4j-economy

# 포트 확인
docker port neo4j-economy
```

---

## 다음 단계

1. **Neo4j 크레덴셜 설정** (지금 바로)
2. **OpenRouter 가입** (5분)
3. **테스트 실행** (수동 트리거)
4. **Twitter API는 나중에** (실제 운영 시)

**예상 소요 시간:** 15분
**초기 비용:** $10 (OpenRouter)

---

**작성자:** Claude Sonnet 4.5
**업데이트:** 2025-12-26
