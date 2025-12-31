# 경제 이벤트 파이프라인 배포 가이드

**생성일:** 2025-12-25
**파이프라인:** X/Twitter → Grok 4.1 → Neo4j Graph DB

---

## 📋 사전 준비 체크리스트

### 1. API 키 & 자격증명

- [ ] **X/Twitter API Access**
  - Bearer Token (read-only 권한)
  - 계정: [Twitter Developer Portal](https://developer.twitter.com/)
  - 필요 권한: `tweet.read`, `users.read`

- [ ] **xAI Grok API**
  - API Key: [xAI Console](https://console.x.ai/)
  - 모델: `x-ai/grok-4.1-fast` (2M context)
  - 월 예산: ~$50-100 (1일 500트윗 가정)

- [ ] **Neo4j 연결**
  - 호스트: `localhost:7688`
  - 인증: `neo4j / regime2025`
  - 브라우저 확인: http://localhost:7475

- [ ] **Slack Webhook (선택사항)**
  - 고신뢰도 이벤트 알림용
  - Webhook URL: https://hooks.slack.com/services/...

### 2. 소프트웨어 설치

```bash
# n8n 설치 (Docker 권장)
docker run -d --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# 또는 npm
npm install n8n -g

# 실행 확인
open http://localhost:5678
```

---

## 🚀 n8n 워크플로우 임포트

### 1단계: n8n 접속

```bash
# n8n 실행 (이미 실행중이면 스킵)
n8n start

# 브라우저에서
open http://localhost:5678
```

### 2단계: 워크플로우 임포트

1. n8n 웹UI에서 **Workflows** → **Import from File**
2. 파일 선택: `/Users/js/g9/n8n_workflows/economic_event_pipeline.json`
3. Import 확인

### 3단계: Credentials 설정

#### Twitter Credentials:
1. **Twitter OAuth2 API** 노드 클릭
2. Credentials → **Create New**
3. 입력:
   - Name: `Twitter-Economic-Monitor`
   - API Key: `[Your Bearer Token]`
4. Save

#### Grok API Credentials:
1. **HTTP Request (Grok)** 노드 클릭
2. Authentication → **Header Auth**
3. 입력:
   - Name: `Authorization`
   - Value: `Bearer [Your xAI API Key]`
4. Save

#### Neo4j Credentials:
1. **Neo4j** 노드 클릭
2. Credentials → **Create New**
3. 입력:
   - Host: `localhost`
   - Port: `7688`
   - User: `neo4j`
   - Password: `regime2025`
   - Database: `neo4j`
4. Save

#### Slack (선택):
1. **Slack** 노드 클릭
2. Webhook URL 입력
3. Save

### 4단계: 화이트리스트 설정

`Switch (Whitelist Check)` 노드 수정:

```javascript
// Tier 1: Central Banks & Government
const tier1 = [
  'federalreserve',  // Fed
  'ecb',             // ECB
  'BIS_org',         // BIS
  'USTreasury'       // 미 재무부
];

// Tier 2: Financial Media
const tier2 = [
  'business',        // Bloomberg
  'markets',         // Bloomberg Markets
  'ReutersMarkets',  // Reuters
  'FT',              // Financial Times
  'WSJ'              // Wall Street Journal
];

// Tier 3: Analysts & Quants
const tier3 = [
  'RaoulGMI',        // Raoul Pal
  'LynAldenContact', // Lyn Alden
  'MacroAlf',        // Alfonso Peccatiello
  'jam_croissant'    // Jawad Mian
];

// 트위터 핸들 추출 (대소문자 무시)
const username = $json.user.username.toLowerCase();

if (tier1.includes(username)) {
  return { tier: 1, trust: 'high' };
} else if (tier2.includes(username)) {
  return { tier: 2, trust: 'medium' };
} else if (tier3.includes(username)) {
  return { tier: 3, trust: 'medium-low' };
} else {
  return null; // 필터링
}
```

---

## ✅ 테스트 & 검증

### 1. 수동 테스트 (워크플로우 실행)

```bash
# n8n에서 워크플로우 활성화
# Test Workflow 버튼 클릭
# 최근 트윗 1개 가져와서 전체 파이프라인 테스트
```

**예상 결과:**
- Twitter 노드: 1개 트윗 수집
- Keyword Filter: 패턴 매칭
- Whitelist: Tier 확인
- Grok: 이벤트 분류
- Neo4j: Event 노드 생성

### 2. Neo4j 검증 쿼리

```cypher
// 1. 이벤트 생성 확인
MATCH (e:Event)
RETURN e.type, e.title, e.confidence, e.timestamp
ORDER BY e.timestamp DESC
LIMIT 5;

// 2. Factor 연결 확인
MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
RETURN e.title, f.name, r.impact_direction, r.impact_magnitude
ORDER BY e.timestamp DESC
LIMIT 5;

// 3. Tier별 이벤트 통계
MATCH (e:Event)
RETURN e.source_tier as tier,
       count(*) as event_count,
       avg(e.confidence) as avg_confidence
ORDER BY tier;
```

### 3. 자동 검증 스크립트

```bash
# 검증 스크립트 실행
python3 /Users/js/g9/scripts/validate_event_pipeline.py

# 예상 출력:
# ✓ Neo4j 연결 성공
# ✓ Event 노드 6개 발견
# ✓ AFFECTS 관계 4개 생성
# ⚠ Tier 1 이벤트 0개 (24시간 내)
# ℹ 평균 confidence: 0.72
```

---

## 📊 모니터링 & 운영

### 1. 일일 헬스 체크

```bash
# 오늘 생성된 이벤트 수
python3 /Users/js/g9/scripts/pipeline_health_check.py

# 출력:
# 📅 2025-12-25 Health Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Twitter 수집:    248 트윗
# 키워드 통과:      89 트윗 (35.9%)
# 화이트리스트:     34 트윗 (13.7%)
# 이벤트 생성:      12 이벤트 (4.8%)
# 고신뢰도(>0.8):    3 이벤트 (25.0%)
```

### 2. 이벤트 대시보드 쿼리

```cypher
// 최근 7일 이벤트 타입별 분포
MATCH (e:Event)
WHERE e.timestamp > datetime() - duration('P7D')
RETURN e.type as event_type,
       count(*) as count,
       avg(e.confidence) as avg_conf
ORDER BY count DESC;

// Tier 1 고신뢰도 이벤트 (즉시 주목 필요)
MATCH (e:Event)
WHERE e.source_tier = 1
  AND e.confidence > 0.8
  AND e.timestamp > datetime() - duration('P1D')
RETURN e.title, e.type, e.confidence, e.url
ORDER BY e.confidence DESC;

// Factor별 영향 집계 (누적 impact)
MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
WHERE e.timestamp > datetime() - duration('P7D')
RETURN f.name as factor,
       sum(CASE WHEN r.impact_direction = 'increase' THEN r.impact_magnitude ELSE -r.impact_magnitude END) as net_impact,
       count(e) as event_count
ORDER BY abs(net_impact) DESC;
```

### 3. Slack 알림 설정

워크플로우에서 **Slack High Confidence** 노드 활성화:

```javascript
// confidence > 0.8인 이벤트만 Slack 전송
if ($json.confidence > 0.8) {
  return {
    channel: '#economic-alerts',
    text: `🚨 *${$json.title}*\n` +
          `Type: ${$json.type}\n` +
          `Confidence: ${($json.confidence * 100).toFixed(0)}%\n` +
          `Source: Tier ${$json.source_tier}\n` +
          `URL: ${$json.url}`
  };
}
```

---

## 🔧 문제 해결

### Q1: n8n에서 Twitter 노드가 트윗을 가져오지 못해요

**A:** API 키 권한 확인:
```bash
# Twitter API 테스트
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.twitter.com/2/users/by/username/federalreserve"

# 200 OK 응답 확인
```

### Q2: Grok API가 429 Too Many Requests 에러

**A:** Rate limit 도달. n8n 워크플로우에서:
- **Schedule Trigger** 간격 늘리기: 5분 → 15분
- 또는 xAI 플랜 업그레이드

### Q3: Neo4j에 Event가 생성되지 않아요

**A:** Cypher 쿼리 디버깅:
```cypher
// Neo4j 브라우저에서 직접 실행
MERGE (e:Event {
  id: 'test-001',
  title: 'Test Event',
  type: 'PolicyChange'
})
SET e.timestamp = datetime(),
    e.confidence = 0.9
RETURN e;

// 삭제
MATCH (e:Event {id: 'test-001'}) DELETE e;
```

### Q4: 이벤트가 너무 많이 생성돼요 (노이즈)

**A:** 필터링 강화:
1. **Keyword Filter** 정규식 엄격화
2. **Whitelist** Tier 3 제거
3. **Grok Prompt**에 `minimum_confidence: 0.7` 추가
4. **Filter (Confidence > 0.6)** 임계값 상향: 0.7 또는 0.8

---

## 📈 확장 로드맵

### Phase 1: 기본 운영 (현재)
- [x] 3-tier 화이트리스트
- [x] 5가지 이벤트 타입
- [x] Factor 연결
- [ ] 7일 운영 검증

### Phase 2: 고도화 (1개월)
- [ ] 레짐 전환 자동 계산
  ```cypher
  MATCH (e:Event)-[:AFFECTS]->(f:InfluenceFactor)
  WHERE e.timestamp > datetime() - duration('P7D')
  WITH f, sum(impact_magnitude) as total_impact
  // VIX/Rate/DXY 변화 계산
  // Family 전환 확률 업데이트
  ```

- [ ] 감성 분석 (Sentiment)
  - Grok에 sentiment 필드 추가
  - `fear_greed_index` 계산

### Phase 3: 실시간 분석 (3개월)
- [ ] FastAPI 엔드포인트
- [ ] 웹사이트 실시간 이벤트 스트림
- [ ] 이벤트 → 섹터 추천 자동화

---

## 💾 백업 & 유지보수

### n8n 워크플로우 백업

```bash
# n8n 데이터 백업
cp -r ~/.n8n /Users/js/g9/backups/n8n_$(date +%Y%m%d)

# 워크플로우만 백업 (Git)
cd /Users/js/g9/n8n_workflows
git add economic_event_pipeline.json
git commit -m "Update: 화이트리스트 추가 (YYYY-MM-DD)"
```

### Neo4j 이벤트 정리

```cypher
// 90일 이전 이벤트 삭제 (선택)
MATCH (e:Event)
WHERE e.timestamp < datetime() - duration('P90D')
DETACH DELETE e;

// 또는 아카이빙
MATCH (e:Event)
WHERE e.timestamp < datetime() - duration('P90D')
SET e:ArchivedEvent
REMOVE e:Event;
```

---

## 📞 다음 단계

1. **즉시:** n8n 워크플로우 임포트 및 Credentials 설정
2. **1주:** 테스트 모드 운영 (Tier 1만, 15분 간격)
3. **검증:** 7일간 50+ 이벤트 수집 확인
4. **확장:** Tier 2-3 추가, 간격 단축 (5분)

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-12-25
**작성자:** Claude Sonnet 4.5
