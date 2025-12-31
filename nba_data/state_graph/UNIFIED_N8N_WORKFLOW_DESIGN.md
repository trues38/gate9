# 통합 n8n 워크플로우 설계 (NBA + Economy)

**목표**: 하나의 워크플로우로 NBA와 경제 이벤트 모두 처리

---

## 🎯 핵심 아이디어

**domain 파라미터로 분기 처리**

```javascript
// 워크플로우 최상단에 Config 노드
const DOMAIN = "nba" or "economy"

// 모든 노드가 이 Config를 참조
```

---

## 📊 통합 워크플로우 구조

```
┌─────────────────────────────────────────────────────────────┐
│  Config (도메인 설정)                                        │
│  domain: "nba" | "economy"                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Trigger (더미 데이터 또는 실제 X Search)                    │
│  - NBA: injury, OUT, lineup                                 │
│  - Economy: rate, inflation, Fed                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Keyword Filter (도메인별 키워드)                            │
│  keywords = getDomainKeywords($node["Config"].json.domain)  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Whitelist Check (도메인별 화이트리스트)                     │
│  accounts = getDomainWhitelist($node["Config"].json.domain) │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  AI Analysis (도메인별 모델 + 프롬프트)                      │
│  model = getDomainModel($node["Config"].json.domain)        │
│  prompt = getDomainPrompt($node["Config"].json.domain)      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Parse JSON (공통 로직)                                      │
│  - 코드 블록 제거                                            │
│  - JSON 파싱                                                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Neo4j 저장 (도메인별 포트)                                  │
│  port = getDomainNeo4jPort($node["Config"].json.domain)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 구현 상세

### Node 1: Config (도메인 설정)

```javascript
// n8n Function Node
return [{
  json: {
    domain: "nba",  // 또는 "economy"

    // 도메인별 설정
    keywords: {
      nba: "(OUT|INACTIVE|RULED OUT|QUESTIONABLE|DOUBTFUL|PROBABLE|LINEUP|STARTING|REFEREE|CREW CHIEF)",
      economy: "(rate|FOMC|inflation|CPI|GDP|recession|QE|QT|taper|hawkish|dovish|payroll|unemployment|sanction|war)"
    },

    whitelist: {
      nba: {
        tier1: ['OfficialNBARefs', 'NBA'],
        tier2: ['ShamsCharania', 'wojespn', 'ChrisBHaynes'],
        tier3: ['RotoWireNBA', 'FantasyLabsNBA']
      },
      economy: {
        tier1: ['federalreserve', 'ecb', 'bankofengland', 'boj_en', 'ustreasury'],
        tier2: ['markets', 'wsj', 'ft', 'reuters', 'yahoofinance'],
        tier3: ['nourielroubini', 'paulkrugman', 'lhsummers', 'raoulgmi']
      }
    },

    models: {
      nba: "x-ai/grok-4.1-fast",
      economy: "google/gemini-2.0-flash-001"
    },

    prompts: {
      nba: "You are an NBA event normalizer. Parse tweet text and extract structured data...",
      economy: "당신은 경제 이벤트 분류 전문가입니다. X 트윗을 입력받아 JSON 형식으로..."
    },

    neo4j: {
      nba: { port: 7687 },
      economy: { port: 7688 }
    }
  }
}];
```

### Node 2: Dummy Data Trigger

```javascript
// n8n Code Node
const config = $node["Config"].json;
const domain = config.domain;

// 도메인별 더미 데이터
const dummyData = {
  nba: {
    id_str: '1234567890',
    text: 'LeBron James (ankle) RULED OUT for tonight vs Warriors',
    created_at: new Date().toISOString(),
    user: { screen_name: 'ShamsCharania' }
  },
  economy: {
    id_str: '9876543210',
    text: 'Fed raises interest rates by 25 basis points. Inflation remains elevated at 3.2%.',
    created_at: new Date().toISOString(),
    user: { screen_name: 'federalreserve' }
  }
};

return [{ json: dummyData[domain] }];
```

### Node 3: Keyword Filter

```javascript
// n8n Filter Node
const config = $node["Config"].json;
const domain = config.domain;
const text = $json.text || $json.full_text;

// 도메인별 키워드 패턴
const pattern = config.keywords[domain];
const regex = new RegExp(pattern, 'i');

return regex.test(text) ? [$input.item] : [];
```

### Node 4: Whitelist Check

```javascript
// n8n Code Node
const config = $node["Config"].json;
const domain = config.domain;
const username = $input.item.json.user.screen_name.toLowerCase();

// 도메인별 화이트리스트
const whitelist = config.whitelist[domain];

let tier = 0;
if (whitelist.tier1.map(a => a.toLowerCase()).includes(username)) {
  tier = 1;
} else if (whitelist.tier2.map(a => a.toLowerCase()).includes(username)) {
  tier = 2;
} else if (whitelist.tier3.map(a => a.toLowerCase()).includes(username)) {
  tier = 3;
}

// 화이트리스트에 없으면 버림
if (tier === 0) {
  return [];
}

return [{
  json: {
    ...$input.item.json,
    source_tier: tier,
    source_account: '@' + $input.item.json.user.screen_name,
    domain: domain  // 도메인 정보 추가
  }
}];
```

### Node 5: AI Analysis (OpenRouter)

```javascript
// n8n HTTP Request Node
const config = $node["Config"].json;
const domain = $json.domain;

// 도메인별 모델과 프롬프트
const model = config.models[domain];
const systemPrompt = config.prompts[domain];

// Request Body
{
  "model": model,
  "messages": [
    {
      "role": "system",
      "content": systemPrompt
    },
    {
      "role": "user",
      "content": $json.text
    }
  ],
  "temperature": 0.1,
  "max_tokens": domain === "nba" ? 500 : 1000
}
```

### Node 6: Parse JSON (공통)

```javascript
// n8n Code Node
const aiResponse = $input.item.json.choices[0].message.content;

// JSON 추출 (코드 블록 제거)
let jsonStr = aiResponse.trim();
if (jsonStr.includes('```json')) {
  jsonStr = jsonStr.split('```json')[1].split('```')[0].trim();
} else if (jsonStr.includes('```')) {
  jsonStr = jsonStr.split('```')[1].split('```')[0].trim();
}

const parsed = JSON.parse(jsonStr);

// 메타데이터 추가
const enriched = {
  ...parsed,
  domain: $json.domain,
  event_id: 'evt_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
  timestamp: $json.created_at || new Date().toISOString(),
  source_account: $json.source_account,
  source_tier: $json.source_tier,
  tweet_id: $json.id_str,
  tweet_text: $json.text,
  processed_at: new Date().toISOString()
};

return [{ json: enriched }];
```

### Node 7: Neo4j 저장

```javascript
// n8n HTTP Request Node
const config = $node["Config"].json;
const domain = $json.domain;

// 도메인별 Neo4j 포트
const neo4jConfig = config.neo4j[domain];
const neo4jPort = neo4jConfig.port;

// URL
const url = `http://localhost:${neo4jPort}/db/neo4j/tx/commit`;

// Cypher 쿼리도 도메인별 분기
const statement = domain === "nba"
  ? `CREATE (e:Event:NBAEvent { ... })`
  : `CREATE (e:Event:EconomicEvent { ... })`;

// Request Body
{
  "statements": [{
    "statement": statement,
    "parameters": { ...$json }
  }]
}
```

---

## 🎨 워크플로우 사용법

### NBA 이벤트 수집
1. Config 노드에서 `domain: "nba"` 설정
2. Execute Workflow
3. NBA 트윗 → Grok 분석 → Neo4j(7687) 저장

### 경제 이벤트 수집
1. Config 노드에서 `domain: "economy"` 설정
2. Execute Workflow
3. 경제 트윗 → Gemini 분석 → Neo4j(7688) 저장

---

## 💡 고급 기능: 듀얼 모드

**하나의 워크플로우로 동시에 두 도메인 처리**

```javascript
// Config 노드를 2개로 분할
return [
  { json: { domain: "nba" } },
  { json: { domain: "economy" } }
];

// 이후 노드들은 각 도메인별로 병렬 실행
```

또는 **Schedule Trigger로 도메인 교대**:
```
NBA: 매일 19:00-23:00 실행 (경기 시간)
Economy: 매일 09:00-17:00 실행 (시장 시간)
```

---

## 📊 이점

### 1. 코드 재사용
- 공통 로직 한번만 작성
- 버그 수정도 한번만
- 유지보수 50% 감소

### 2. 확장성
- 새 도메인 추가 쉬움 (예: crypto, politics)
- Config에 설정만 추가하면 됨

### 3. 일관성
- 모든 도메인이 동일한 품질
- 테스트 용이

### 4. 비용 효율
- 하나의 n8n 인스턴스
- 하나의 OpenRouter API 키

---

## 🚀 구현 순서

### Phase 1: 더미 데이터로 검증
1. Config 노드 생성
2. 더미 데이터 노드 (domain별 분기)
3. 나머지 노드들 domain 파라미터 사용
4. NBA 모드로 테스트
5. Economy 모드로 테스트

### Phase 2: 실제 데이터 연결 (선택)
1. 더미 노드를 X Search로 교체
2. 또는 수동 입력 노드 추가

---

## ⚠️ 주의사항

### Neo4j 포트 관리
```
NBA:     localhost:7687
Economy: localhost:7688

→ 도메인별로 다른 DB 사용
→ 데이터 격리 보장
```

### 환경변수
```bash
OPENROUTER_API_KEY=...  # 공통
NEO4J_NBA_PASSWORD=...
NEO4J_ECONOMY_PASSWORD=...
```

### 로그 구분
```
domain 필드로 자동 구분
"domain": "nba" or "economy"
```

---

**작성자**: Claude Code
**버전**: v1.0
**다음 단계**: 통합 워크플로우 구현
