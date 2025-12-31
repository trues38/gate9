# n8n NBA 실시간 파이프라인 배포 가이드

## 개요

**완전 자동화된 NBA 실시간 이벤트 처리 시스템**

```
X 트윗 → n8n 필터링 → Grok 정규화 → Neo4j 저장 → Claude 분석 → Telegram 알림
```

---

## 시스템 아키텍처

### 전체 흐름

```
① X (공식/화이트리스트 계정)
      ↓
② n8n Trigger (1분마다)
   - 새 트윗 감지
   - 계정 화이트리스트
      ↓
③ 1차 필터 (n8n)
   - 키워드: OUT/LINEUP/REF/INACTIVE
   - 정규식 매칭
      ↓
④ 의미 판단 (n8n Function)
   - 스팸 제거
   - 유효 패턴 검증
      ↓
⑤ Grok 4.1 Fast (OpenRouter)
   - 트윗 → 구조화된 JSON
   - 표현 정규화 (OUT/ruled out → OUT)
      ↓
⑥ Event 구조화 (n8n Function)
   - 메타데이터 추가
   - JSON 파싱
      ↓
⑦ Neo4j - Event 저장
   - Event 노드 생성
   - Player/Team 관계 연결
      ↓
⑧ Neo4j - Context 계산
   - 과거 유사 상황 검색
   - 패턴 분석
      ↓
⑨ Claude Sonnet 4.5
   - Impact Assessment
   - Betting Implications
   - 리포트 생성
      ↓
⑩ Telegram 알림
   - 실시간 푸시 알림
```

---

## 사전 준비

### 1. n8n 설치

**Self-hosted** (권장 - 무료):

```bash
# Docker Compose
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your-password
      - WEBHOOK_URL=http://localhost:5678/
    volumes:
      - n8n_data:/home/node/.n8n
volumes:
  n8n_data:
```

```bash
docker-compose up -d
```

**Cloud** (유료):
- https://n8n.cloud (월 $20부터)

### 2. API Keys 발급

필요한 API Keys:

| 서비스 | 용도 | 발급처 | 월 비용 (예상) |
|--------|------|--------|----------------|
| Twitter API | 트윗 감지 | https://developer.twitter.com | $100 (Basic) |
| OpenRouter | Grok 호출 | https://openrouter.ai/keys | $0.50 |
| Anthropic | Claude 리포트 | https://console.anthropic.com | $2-5 |
| Telegram Bot | 알림 발송 | @BotFather | 무료 |

**총 예상 비용**: ~$103/월

### 3. Neo4j 접속 정보

기존 Neo4j 인스턴스 사용:
- URI: `bolt://localhost:7687`
- Username: `neo4j`
- Password: (설정값)

---

## 배포 단계

### Step 1: n8n Credentials 설정

n8n 웹 UI → Settings → Credentials

#### 1-1. Twitter OAuth2

```yaml
Name: Twitter OAuth2
Type: Twitter OAuth2 API

Settings:
  Client ID: (Twitter Developer Portal에서 발급)
  Client Secret: (Twitter Developer Portal에서 발급)
  OAuth Redirect URL: http://localhost:5678/rest/oauth2-credential/callback
```

**Twitter Developer Portal 설정**:
1. https://developer.twitter.com/en/portal/dashboard
2. Projects & Apps → Create App
3. User authentication settings → OAuth 2.0
4. Callback URL: `http://localhost:5678/rest/oauth2-credential/callback`
5. Keys and tokens → Copy Client ID, Client Secret

#### 1-2. Neo4j

```yaml
Name: Neo4j
Type: Neo4j

Settings:
  URI: bolt://localhost:7687
  Username: neo4j
  Password: your-neo4j-password
```

#### 1-3. Telegram Bot

```yaml
Name: Telegram
Type: Telegram API

Settings:
  Access Token: (BotFather에서 발급)
```

**Telegram Bot 생성**:
1. Telegram 앱에서 @BotFather 검색
2. `/newbot` 명령
3. 봇 이름 입력
4. Access Token 복사
5. `/start` 명령으로 봇 활성화
6. Chat ID 확인: https://api.telegram.org/bot<TOKEN>/getUpdates

#### 1-4. Environment Variables

n8n Settings → Variables:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_CHAT_ID=123456789
```

---

### Step 2: 워크플로우 Import

1. n8n 웹 UI → Workflows → Import from File
2. 파일 선택: `n8n_nba_realtime_workflow.json`
3. Import 클릭

---

### Step 3: Credentials 연결

Import된 워크플로우의 각 노드에 Credentials 연결:

| 노드 이름 | Credential Type | Credential Name |
|-----------|-----------------|-----------------|
| X Watch - Official Accounts | Twitter OAuth2 API | Twitter OAuth2 |
| Neo4j - Event 저장 | Neo4j | Neo4j |
| Neo4j - Context 계산 | Neo4j | Neo4j |
| Telegram - 알림 발송 | Telegram API | Telegram |

---

### Step 4: 워크플로우 활성화

1. 워크플로우 상단의 **Inactive** 토글 → **Active**
2. 1분마다 자동 실행 시작

---

## 테스트

### 수동 테스트

워크플로우에서 "Execute Workflow" 클릭:

**예상 결과**:
```
✅ X Watch - Official Accounts: 10 items
✅ 1차 필터 - 키워드: 3 items (필터링됨)
✅ 의미 판단: 2 items (스팸 제거)
✅ Grok 정규화: 2 items (JSON 출력)
✅ Event 구조화: 2 items
✅ Neo4j - Event 저장: 2 nodes created
✅ Neo4j - Context 계산: 2 items
✅ Claude - 리포트 생성: 2 items
✅ Telegram - 알림 발송: 2 messages sent
```

### Telegram 알림 확인

Telegram 봇으로부터 메시지 수신:

```
🚨 NBA Real-time Alert

Impact Assessment: 8/10

Player: Luka Doncic
Team: DAL
Status: OUT (ankle injury)
Game: DAL vs GSW

Historical Pattern:
- Last OUT: 7 games ago (knee soreness)
- Total OUT this season: 3 games
- Team record without Luka: 1-2

Betting Implications:
- Spread impact: +5.5 points to GSW
- O/U likely shifts down 4-5 points
- DAL win probability drops from 52% to 28%

Confidence Level: HIGH (0.95)

---
Source: @ShamsCharania
Processed: 2025-12-25T16:30:00Z
```

---

## 모니터링

### n8n 실행 로그

Workflows → Executions:

실시간 확인:
- 실행 시간
- 성공/실패 상태
- 각 노드 출력

### Neo4j 데이터 확인

Neo4j Browser:

```cypher
// 최근 Event 10개
MATCH (e:Event)
RETURN e
ORDER BY e.processed_at DESC
LIMIT 10
```

```cypher
// Event → Player 관계
MATCH (e:Event)-[:AFFECTS_PLAYER]->(p:Player)
WHERE e.status = 'OUT'
RETURN p.name, count(e) as out_count
ORDER BY out_count DESC
```

### OpenRouter 사용량

https://openrouter.ai/activity

확인 항목:
- 일일 요청 수
- 토큰 사용량
- 누적 비용

---

## 고급 설정

### 1. 알림 필터링 (고신뢰도만)

"Telegram - 알림 발송" 노드 전에 Filter 추가:

```javascript
// Confidence threshold
if ($json.confidence < 0.8) {
  return [];  // 0.8 미만은 알림 안 함
}
return [$input.item];
```

### 2. 배치 처리 (비용 절감)

"Grok 정규화" 노드를 5분마다 실행하도록 변경:

```javascript
// n8n Function으로 5개씩 모아서 처리
const items = $input.all();
const batches = [];

for (let i = 0; i < items.length; i += 5) {
  batches.push(items.slice(i, i + 5));
}

return batches.map(batch => ({
  json: {
    tweets: batch.map(item => item.json.full_text)
  }
}));
```

### 3. 중복 방지

Neo4j 쿼리에 이미 포함:

```cypher
MERGE (e:Event {tweet_id: $tweet_id})
```

→ 같은 tweet_id는 한 번만 생성

---

## 화이트리스트 계정 관리

### 현재 설정

"X Watch - Official Accounts" 노드:

```
from:OfficialNBARefs OR from:ShamsCharania OR from:ChrisBHaynes OR from:RotoWireNBA
```

### 계정 추가

1. n8n 워크플로우 편집
2. "X Watch - Official Accounts" 노드 클릭
3. Search Text 수정:

```
from:OfficialNBARefs OR
from:ShamsCharania OR
from:ChrisBHaynes OR
from:RotoWireNBA OR
from:wojespn OR              # Adrian Wojnarowski (ESPN)
from:BobbyMarks42 OR         # ESPN Analyst
from:FantasyLabsNBA          # Fantasy Labs
```

4. Save

---

## 비용 최적화

### 1. Twitter API 대안

Twitter API $100/월이 부담되면:

**옵션 A**: RSS Feed 사용 (무료)
- Nitter 인스턴스: https://nitter.net/
- RSS: https://nitter.net/ShamsCharania/rss

**옵션 B**: Webhook (Twitter Pro $5/월)
- Zapier → Twitter Watch → Webhook → n8n

### 2. Grok 호출 빈도 조절

1차 필터를 더 엄격하게:

```javascript
// 키워드 + 계정 동시 만족
const validAccounts = ['OfficialNBARefs', 'ShamsCharania', 'ChrisBHaynes'];
const validKeywords = ['OUT', 'INACTIVE', 'QUESTIONABLE'];

if (!validAccounts.includes($json.user.screen_name)) {
  return [];
}

const hasKeyword = validKeywords.some(kw =>
  $json.full_text.toUpperCase().includes(kw)
);

if (!hasKeyword) {
  return [];
}

return [$input.item];
```

→ **Grok 호출 50-70% 감소**

---

## 트러블슈팅

### Twitter API Rate Limit

**증상**: "Rate limit exceeded"

**해결**:
1. Poll 간격 늘리기: 1분 → 5분
2. Search 쿼리 최적화 (계정 수 줄이기)

### Grok 응답 파싱 실패

**증상**: "JSON parse error"

**해결**:
"Event 구조화" 노드에 예외 처리 추가:

```javascript
try {
  const event = JSON.parse(jsonContent);
  return { json: event };
} catch (error) {
  console.error('JSON parse failed:', error);
  return {
    json: {
      error: 'parse_failed',
      raw_content: content
    }
  };
}
```

### Neo4j 연결 실패

**증상**: "Connection refused"

**해결**:
1. Neo4j 실행 확인: `docker ps | grep neo4j`
2. URI 확인: `bolt://localhost:7687` (http가 아님)
3. 방화벽 확인: `telnet localhost 7687`

### Telegram 알림 안 옴

**증상**: 알림이 발송되지 않음

**해결**:
1. Chat ID 확인:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
2. 봇과 대화 시작: Telegram에서 `/start` 전송
3. 환경변수 확인: `echo $TELEGRAM_CHAT_ID`

---

## 프로덕션 체크리스트

배포 전 확인:

- [ ] Twitter OAuth2 인증 완료
- [ ] OpenRouter API Key 설정 및 크레딧 충전 ($5+)
- [ ] Anthropic API Key 설정 및 크레딧 충전 ($5+)
- [ ] Telegram Bot 생성 및 Chat ID 확인
- [ ] Neo4j 연결 테스트 성공
- [ ] n8n 워크플로우 수동 실행 성공
- [ ] Telegram 테스트 메시지 수신 확인
- [ ] 1시간 동안 자동 실행 모니터링
- [ ] 로그에 에러 없음 확인
- [ ] 비용 추적 대시보드 설정

---

## 유지보수

### 일일 점검

- [ ] n8n Executions 에러 확인
- [ ] OpenRouter 사용량 확인 (예산 초과 방지)
- [ ] Telegram 알림 품질 확인 (너무 많거나 적지 않은지)

### 주간 점검

- [ ] Neo4j 데이터베이스 크기 확인
- [ ] 중복 Event 노드 확인 및 정리
- [ ] API 키 만료일 확인
- [ ] 화이트리스트 계정 업데이트 (새 기자 추가)

### 월간 점검

- [ ] 비용 리포트 생성 및 분석
- [ ] 시스템 성능 최적화
- [ ] 백업 설정 확인

---

## 다음 단계

### Phase 1: 안정화 (1주일)
- 시스템 모니터링
- 알림 품질 개선
- 버그 수정

### Phase 2: 고도화 (2-4주)
- Grok Reasoning 모드 활용
- Multi-turn conversation (애매한 경우)
- 신뢰도 기반 자동 베팅 시그널

### Phase 3: 확장 (1-3개월)
- NFL/MLB 등 다른 스포츠 추가
- 프롭벳 자동 분석
- 백테스팅 시스템 구축

---

## 참고 자료

### n8n
- 공식 문서: https://docs.n8n.io/
- Twitter 노드: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.twitter/
- Neo4j 노드: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.neo4j/

### OpenRouter
- Grok 4.1 Fast: https://openrouter.ai/x-ai/grok-4.1-fast
- API 문서: https://openrouter.ai/docs

### Anthropic
- Claude API: https://docs.anthropic.com/
- Pricing: https://www.anthropic.com/pricing

---

## 요약

✅ **완전 자동화된 NBA 실시간 파이프라인**

**구성 요소**:
- n8n (오케스트레이션)
- Grok 4.1 Fast (이벤트 정규화)
- Neo4j (그래프 저장)
- Claude Sonnet 4.5 (리포트 생성)
- Telegram (알림)

**예상 비용**: ~$103/월
- Twitter API: $100
- OpenRouter (Grok): $0.50
- Anthropic (Claude): $2-5
- Telegram: 무료

**배포 시간**: 2-3시간

**즉시 시작**:
```bash
# n8n 실행
docker-compose up -d

# 워크플로우 Import
# n8n_nba_realtime_workflow.json

# Credentials 설정
# → API Keys 입력

# 활성화
# → Active 토글
```

**모니터링**:
- n8n Executions
- OpenRouter Activity
- Neo4j Browser
- Telegram 알림
