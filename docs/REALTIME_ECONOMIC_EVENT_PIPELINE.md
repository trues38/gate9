# 실시간 경제 이벤트 파이프라인 설계

NBA 모델의 트윗 기반 파이프라인을 경제 레짐 분석에 적용

---

## 🎯 핵심 개념

**NBA → 경제 매핑:**

| NBA | 경제 |
|-----|------|
| 선수 부상/복귀 | 금리 인상/인하 |
| 라인업 변경 | 정책 발표 |
| 레퍼리 배정 | 지정학 긴장 |
| OUT/INACTIVE | QE/QT 시작/종료 |
| 공식 계정 | 연준/ECB/블룸버그 |
| 의미 판단 | 시장 영향도 판단 |
| Event → GameState | Event → MarketState |

---

## 📊 파이프라인 아키텍처

```
① X (화이트리스트 계정)
   - @FederalReserve
   - @ECB
   - @BoJ_official
   - @markets (블룸버그)
   - @WSJ, @FT
   - 저명 경제학자/퀀트
      ↓
② n8n Trigger
   - 새 트윗 감지
   - 수정/추가 확인
   - 멘션/리트윗 필터
      ↓
③ 1차 필터 (n8n)
   - 화이트리스트 검증
   - 키워드 매칭:
     * FOMC, 금리, rate
     * QE, QT, taper
     * inflation, CPI
     * geopolitical, war
     * recession, GDP
      ↓
④ "시장 영향력 있는가?" 판단
   - 아니면 → 버림
   - 맞으면 → Grok 호출
      ↓
⑤ Grok X Search
   - 트윗 맥락 확장
   - 후속 트윗/반응
   - 표현 정규화
     (예: "lift off" = 금리 인상)
      ↓
⑥ Event 구조화
   - PolicyChange
   - GeopoliticalEvent
   - EconomicData
   - SentimentShift
   - 신뢰도 부여
      ↓
⑦ Neo4j Event 노드 생성
   - Event → Regime 연결
   - Event → Factor 연결
   - Event → Sector 영향 계산
      ↓
⑧ Context 재계산
   - 유사 과거 이벤트
   - Regime 전환 확률 업데이트
   - 섹터 영향도 계산
   - 실시간 알림/리포트
```

---

## 🎖️ 화이트리스트 계정 (예시)

### Tier 1: 공식 기관
```python
TIER1_ACCOUNTS = {
    "central_banks": [
        "@federalreserve",    # 연준
        "@ecb",               # 유럽중앙은행
        "@bankofengland",     # 영란은행
        "@boj_en",            # 일본은행
    ],
    "government": [
        "@USTreasury",        # 미 재무부
        "@WhiteHouse",        # 백악관 (경제 발표)
    ],
    "statistics": [
        "@BLS_gov",           # 미 노동부 (고용 지표)
        "@CommerceGov",       # 상무부 (GDP)
    ]
}
```

### Tier 2: 신뢰 언론사
```python
TIER2_ACCOUNTS = {
    "financial_media": [
        "@markets",           # 블룸버그
        "@WSJ",              # 월스트리트저널
        "@FT",               # 파이낸셜타임스
        "@Reuters",          # 로이터
        "@YahooFinance",
    ],
    "reporters": [
        "@NickTimiraos",     # WSJ 연준 담당
        "@jeannasmialek",    # NYT 연준 담당
        "@LizAnnSonders",    # 찰스슈왑 수석
    ]
}
```

### Tier 3: 저명 분석가/퀀트
```python
TIER3_ACCOUNTS = {
    "economists": [
        "@NourielRoubini",   # 누리엘 루비니
        "@PaulKrugman",      # 폴 크루그먼
        "@LHSummers",        # 래리 서머스
    ],
    "quants": [
        "@RaoulGMI",         # Raoul Pal (매크로)
        "@LynAldenContact",  # Lyn Alden
        "@adam_tooze",       # 경제사학자
    ],
    "crypto_macro": [
        "@APompliano",       # 앤서니 폼플리아노
        "@woonomic",         # Woo (온체인 분석)
    ]
}
```

---

## 🔍 키워드 & 정규식

### 금융정책 (Monetary Policy)
```python
POLICY_KEYWORDS = {
    "rate_change": [
        r"(?i)(raise|hike|cut|lower)\s*(interest\s*)?rates?",
        r"(?i)fed\s*funds?\s*rate",
        r"(?i)(25|50|75)\s*(bp|basis\s*points?)",
        r"(?i)lift[\s-]?off",
    ],
    "qe_qt": [
        r"(?i)quantitative\s*easing",
        r"(?i)QE|QT",
        r"(?i)taper(ing)?",
        r"(?i)balance\s*sheet",
    ],
    "forward_guidance": [
        r"(?i)dot\s*plot",
        r"(?i)FOMC\s*(statement|minutes)",
        r"(?i)(hawkish|dovish)",
    ]
}
```

### 경제 지표 (Economic Data)
```python
DATA_KEYWORDS = {
    "inflation": [
        r"(?i)CPI|inflation",
        r"(?i)PCE",
        r"(?i)core\s*inflation",
    ],
    "employment": [
        r"(?i)non[\s-]?farm\s*payrolls?",
        r"(?i)NFP",
        r"(?i)unemployment\s*rate",
        r"(?i)jobless\s*claims",
    ],
    "growth": [
        r"(?i)GDP",
        r"(?i)recession",
        r"(?i)PMI",
    ]
}
```

### 지정학 (Geopolitics)
```python
GEO_KEYWORDS = {
    "conflicts": [
        r"(?i)(war|conflict|invasion)",
        r"(?i)(sanction|embargo)",
        r"(?i)(Ukraine|Russia|China|Taiwan)",
    ],
    "trade": [
        r"(?i)tariff",
        r"(?i)trade\s*(war|deal)",
    ]
}
```

---

## 📦 Event 스키마 (Neo4j)

### Event 노드 정의
```cypher
(:Event {
  event_id: STRING,              // "evt_20251225_001"
  type: STRING,                  // "PolicyChange", "GeopoliticalEvent"
  timestamp: DATETIME,

  // 출처
  source_account: STRING,        // "@federalreserve"
  source_tier: INTEGER,          // 1-3
  tweet_id: STRING,
  tweet_url: STRING,

  // 내용
  title: STRING,                 // "연준 금리 0.25%p 인상"
  description: STRING,
  keywords: LIST<STRING>,        // ["금리인상", "FOMC", "hawkish"]

  // 구조화된 정보
  magnitude: FLOAT,              // 0.25 (25bp)
  direction: STRING,             // "up", "down", "neutral"
  affected_factors: LIST<STRING>, // ["금리", "달러"]

  // 신뢰도
  confidence: FLOAT,             // 0.95
  verification_status: STRING,   // "confirmed", "rumor", "pending"

  // Grok 확장 정보
  context_summary: STRING,
  related_tweets: LIST<STRING>,
  market_reaction: STRING
})
```

### Event 타입 정의
```python
EVENT_TYPES = {
    "PolicyChange": {
        "description": "금융정책 변경",
        "subtypes": ["rate_hike", "rate_cut", "qe_start", "qt_start"],
        "magnitude_required": True,
        "affected_factors": ["금리", "유동성"]
    },

    "EconomicData": {
        "description": "주요 경제지표 발표",
        "subtypes": ["cpi", "nfp", "gdp", "pmi"],
        "magnitude_required": True,
        "affected_factors": ["심리", "금리"]
    },

    "GeopoliticalEvent": {
        "description": "지정학적 이벤트",
        "subtypes": ["conflict", "sanction", "trade_war"],
        "magnitude_required": False,
        "affected_factors": ["심리", "유동성"]
    },

    "SentimentShift": {
        "description": "시장 심리 변화",
        "subtypes": ["panic", "euphoria", "uncertainty"],
        "magnitude_required": False,
        "affected_factors": ["심리"]
    },

    "MarketShock": {
        "description": "예상치 못한 충격",
        "subtypes": ["flash_crash", "circuit_breaker", "bank_collapse"],
        "magnitude_required": True,
        "affected_factors": ["심리", "유동성", "금리"]
    }
}
```

---

## 🔗 Event 관계 (Neo4j)

### 1. Event → Regime
```cypher
(Event)-[:TRIGGERS {
  probability: FLOAT,        // 레짐 전환 확률
  lag_hours: INTEGER,        // 지연 시간
  historical_cases: INTEGER  // 과거 사례 수
}]->(Regime)

예: (금리인상)-[:TRIGGERS {probability: 0.65, lag_hours: 48}]->(수축)
```

### 2. Event → Factor
```cypher
(Event)-[:IMPACTS {
  magnitude: FLOAT,          // -1.0 ~ +1.0
  duration_days: INTEGER,    // 영향 지속 기간
  confidence: FLOAT
}]->(InfluenceFactor)

예: (금리인상)-[:IMPACTS {magnitude: 0.8, duration: 30}]->(금리)
```

### 3. Event → Sector
```cypher
(Event)-[:AFFECTS {
  expected_return: FLOAT,    // 예상 수익률
  win_rate: FLOAT,
  sample_size: INTEGER
}]->(Sector)

예: (금리인상)-[:AFFECTS {expected_return: -7.5, win_rate: 0.68}]->(기술주)
```

### 4. Event → Event (선행/후행)
```cypher
(Event)-[:LEADS_TO {
  probability: FLOAT,
  avg_lag_days: INTEGER
}]->(Event)

예: (고용지표악화)-[:LEADS_TO {probability: 0.7, lag: 14}]->(금리인하)
```

---

## 🤖 Grok 프롬프트 (Event 구조화)

```python
GROK_SYSTEM_PROMPT = """
당신은 경제 이벤트 분류 전문가입니다.

입력: X 트윗 + 관련 트윗 스레드
출력: 구조화된 Event JSON

규칙:
1. 시장 영향력 판단 (significant: true/false)
2. Event 타입 분류 (PolicyChange, EconomicData 등)
3. magnitude 추출 (25bp, 2.5%, $85B 등)
4. direction 판단 (up, down, neutral)
5. affected_factors 추론
6. confidence 계산 (출처 tier + 명확성)

예시:
트윗: "@federalreserve: The Federal Reserve raised the target range for the federal funds rate by 25 basis points to 5.25-5.50%"

출력:
{
  "significant": true,
  "type": "PolicyChange",
  "subtype": "rate_hike",
  "magnitude": 0.25,
  "direction": "up",
  "affected_factors": ["금리", "달러"],
  "confidence": 0.98,
  "title": "연준 금리 0.25%p 인상",
  "description": "연준이 기준금리를 5.25-5.50%로 인상",
  "keywords": ["금리인상", "FOMC", "hawkish"]
}
"""
```

---

## 🔄 실시간 Context 재계산

### Event 발생 시 자동 실행

**1. 유사 과거 이벤트 검색**
```cypher
MATCH (new:Event {event_id: $new_event_id})
MATCH (past:Event)
WHERE past.type = new.type
  AND past.timestamp < new.timestamp
  AND abs(past.magnitude - new.magnitude) < 0.1

WITH new, past,
     abs(past.magnitude - new.magnitude) as distance
ORDER BY distance ASC
LIMIT 5

// 과거 이벤트 후 Regime 전환 패턴 확인
MATCH (past)-[:TRIGGERS]->(regime:Regime)
RETURN regime.name, count(*) as cases, avg(t.probability) as avg_prob
```

**2. Regime 전환 확률 업데이트**
```cypher
MATCH (event:Event {event_id: $event_id})
MATCH (current_regime:Regime)<-[:IN_REGIME]-(market:MarketState)
WHERE market.date = date()

// 유사 과거 이벤트의 전환 패턴
MATCH (past:Event)-[:TRIGGERS {lag_hours: $lag}]->(next_regime:Regime)
WHERE past.type = event.type
  AND abs(past.magnitude - event.magnitude) < 0.2

WITH next_regime, count(*) as cases, avg(t.probability) as prob
ORDER BY cases DESC

// 전환 확률 업데이트
MERGE (current_regime)-[t:LIKELY_TRANSITION]->(next_regime)
SET t.probability = prob,
    t.triggered_by = $event_id,
    t.updated_at = datetime()
```

**3. 섹터 영향도 재계산**
```cypher
MATCH (event:Event {event_id: $event_id})
MATCH (event)-[:AFFECTS]->(sector:Sector)
MATCH (event)-[:TRIGGERS]->(regime:Regime)

// 해당 Regime에서 Sector 성과 조정
MATCH (sector)-[perf:OUTPERFORMS_IN]->(regime)
SET perf.recent_event_impact = event.expected_return,
    perf.confidence = perf.confidence * event.confidence
```

---

## 📊 n8n 워크플로우 (구체적)

### Workflow 1: 트윗 모니터링
```javascript
// 1. Twitter Trigger (5분마다)
{
  "node": "Twitter Monitor",
  "type": "n8n-nodes-base.twitter",
  "operation": "search",
  "parameters": {
    "searchText": "from:federalreserve OR from:ecb OR from:markets",
    "returnAll": false,
    "limit": 100
  }
}

// 2. 중복 제거
{
  "node": "Remove Duplicates",
  "type": "n8n-nodes-base.removeDuplicates",
  "parameters": {
    "compare": "id"
  }
}

// 3. 1차 필터
{
  "node": "Keyword Filter",
  "type": "n8n-nodes-base.filter",
  "parameters": {
    "conditions": {
      "string": [
        {
          "value1": "={{ $json.text }}",
          "operation": "regex",
          "value2": "(rate|FOMC|inflation|CPI|GDP|recession)"
        }
      ]
    }
  }
}

// 4. 화이트리스트 검증
{
  "node": "Whitelist Check",
  "type": "n8n-nodes-base.function",
  "parameters": {
    "functionCode": `
      const TIER1 = ['federalreserve', 'ecb', 'bankofengland'];
      const TIER2 = ['markets', 'WSJ', 'FT'];
      const TIER3 = ['NourielRoubini', 'RaoulGMI'];

      const username = $input.item.json.user.screen_name.toLowerCase();
      let tier = 0;

      if (TIER1.includes(username)) tier = 1;
      else if (TIER2.includes(username)) tier = 2;
      else if (TIER3.includes(username)) tier = 3;

      if (tier === 0) return [];  // 차단

      return [{
        json: {
          ...$input.item.json,
          source_tier: tier
        }
      }];
    `
  }
}
```

### Workflow 2: Grok 분석
```javascript
// 5. Grok API 호출
{
  "node": "Grok Analysis",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "https://api.x.ai/v1/chat/completions",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "grokApi",
    "sendBody": true,
    "bodyParameters": {
      "model": "grok-2-latest",
      "messages": [
        {
          "role": "system",
          "content": "{{ $node['Prompt Template'].json.system_prompt }}"
        },
        {
          "role": "user",
          "content": "트윗: {{ $json.text }}"
        }
      ],
      "temperature": 0.1
    }
  }
}

// 6. JSON 파싱
{
  "node": "Parse Grok Response",
  "type": "n8n-nodes-base.function",
  "parameters": {
    "functionCode": `
      const response = JSON.parse($input.item.json.choices[0].message.content);

      // significant가 false면 버림
      if (!response.significant) return [];

      return [{
        json: {
          ...$input.item.json,
          ...response,
          event_id: 'evt_' + Date.now()
        }
      }];
    `
  }
}
```

### Workflow 3: Neo4j 저장
```javascript
// 7. Neo4j Event 생성
{
  "node": "Create Event Node",
  "type": "n8n-nodes-base.neo4j",
  "parameters": {
    "operation": "executeQuery",
    "query": `
      CREATE (e:Event {
        event_id: $event_id,
        type: $type,
        subtype: $subtype,
        timestamp: datetime($timestamp),
        source_account: $source_account,
        source_tier: $source_tier,
        tweet_id: $tweet_id,
        tweet_url: $tweet_url,
        title: $title,
        description: $description,
        keywords: $keywords,
        magnitude: $magnitude,
        direction: $direction,
        affected_factors: $affected_factors,
        confidence: $confidence
      })
      RETURN e
    `
  }
}

// 8. Event → Factor 관계
{
  "node": "Link to Factors",
  "type": "n8n-nodes-base.neo4j",
  "parameters": {
    "operation": "executeQuery",
    "query": `
      MATCH (e:Event {event_id: $event_id})
      UNWIND $affected_factors as factor_name
      MATCH (f:InfluenceFactor {name: factor_name})
      MERGE (e)-[i:IMPACTS]->(f)
      SET i.magnitude = $magnitude,
          i.confidence = $confidence
    `
  }
}

// 9. Context 재계산 트리거
{
  "node": "Trigger Recalculation",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "http://localhost:8000/api/recalculate",
    "sendBody": true,
    "bodyParameters": {
      "event_id": "={{ $json.event_id }}"
    }
  }
}
```

---

## 📱 실시간 알림 (선택적)

### 고영향 이벤트 알림
```python
# Slack / Discord Webhook
HIGH_IMPACT_THRESHOLD = 0.8

def send_alert(event):
    if event['confidence'] >= HIGH_IMPACT_THRESHOLD:
        message = f"""
🚨 고영향 경제 이벤트 감지

**타입:** {event['type']} ({event['subtype']})
**출처:** {event['source_account']} (Tier {event['source_tier']})
**내용:** {event['title']}

**영향 예상:**
"""
        for sector, impact in event['sector_impacts'].items():
            emoji = "🔺" if impact > 0 else "🔻"
            message += f"{emoji} {sector}: {impact:+.1f}%\n"

        message += f"\n**신뢰도:** {event['confidence']*100:.0f}%"

        send_to_slack(message)
```

---

## 🎯 실전 예시

### 예시 1: 연준 금리 인상
```
[트윗]
@federalreserve: The Federal Reserve raised the target range for the federal funds rate by 25 basis points to 5.25-5.50%.

[1차 필터] ✅ 통과
- 계정: federalreserve (Tier 1)
- 키워드: "raised", "federal funds rate", "25 basis points"

[Grok 분석]
{
  "significant": true,
  "type": "PolicyChange",
  "subtype": "rate_hike",
  "magnitude": 0.25,
  "direction": "up",
  "affected_factors": ["금리", "달러"],
  "confidence": 0.98,
  "title": "연준 금리 0.25%p 인상"
}

[Neo4j Event 생성]
(:Event {
  event_id: "evt_20251225_001",
  type: "PolicyChange",
  magnitude: 0.25,
  confidence: 0.98
})

[관계 생성]
(evt_001)-[:IMPACTS {magnitude: 0.8}]->(금리)
(evt_001)-[:TRIGGERS {probability: 0.65}]->(수축)
(evt_001)-[:AFFECTS {expected_return: -7.5}]->(기술주)

[실시간 업데이트]
- Equity Complacency → 수축 전환 확률: 34.6% → 65.2%
- 기술주 추천도: +4.3% → -7.5%
- 방어주 추천도: -4.3% → +8.2%
```

### 예시 2: 지정학적 긴장
```
[트윗]
@markets: BREAKING: US announces new sanctions on Russia's energy sector

[1차 필터] ✅ 통과
- 계정: markets (Tier 2)
- 키워드: "sanctions", "Russia", "energy"

[Grok 분석]
{
  "significant": true,
  "type": "GeopoliticalEvent",
  "subtype": "sanction",
  "magnitude": null,
  "direction": "neutral",
  "affected_factors": ["심리", "에너지"],
  "confidence": 0.75,
  "title": "러시아 에너지 부문 제재"
}

[Neo4j Event]
(evt_002)-[:TRIGGERS {probability: 0.45}]->(Geopolitical Tension Fog)
(evt_002)-[:AFFECTS {expected_return: +6.5}]->(에너지)
(evt_002)-[:AFFECTS {expected_return: -4.0}]->(기술주)
```

---

## 🚀 Phase별 구현 계획

### Phase 1: MVP (1주)
- [ ] n8n 설치 및 트윗 모니터링
- [ ] Tier 1 계정 10개만
- [ ] 간단한 키워드 필터
- [ ] Neo4j Event 노드 수동 생성

### Phase 2: 자동화 (2주)
- [ ] Grok API 연동
- [ ] Event 자동 구조화
- [ ] Event → Regime/Factor 관계 자동 생성
- [ ] Tier 2-3 계정 추가

### Phase 3: Context 재계산 (3주)
- [ ] 유사 과거 이벤트 검색
- [ ] Regime 전환 확률 업데이트
- [ ] 섹터 영향도 재계산
- [ ] 실시간 대시보드

### Phase 4: 고도화 (4주+)
- [ ] Slack/Discord 알림
- [ ] 백테스팅 (과거 이벤트 검증)
- [ ] 신뢰도 점수 정교화
- [ ] Event → Event 선행/후행 관계

---

## 💡 NBA vs 경제 비교

| 항목 | NBA | 경제 |
|------|-----|------|
| **데이터 소스** | 공식 계정, 기자 | 연준, 블룸버그 |
| **이벤트 타입** | Injury, Lineup | PolicyChange, GeopoliticalEvent |
| **키워드** | OUT, INACTIVE | rate hike, QE, sanction |
| **영향 대상** | GameState, 승률 | Regime, 섹터 수익률 |
| **신뢰도** | 공식 > 기자 > 루머 | Tier 1 > Tier 2 > Tier 3 |
| **실시간성** | 경기 4시간 전 | 이벤트 발생 즉시 |
| **검증** | 라인업 공식 발표 | 정책 공식 문서 |

---

**완벽히 동일한 로직입니다!** 🎯

이제 n8n 워크플로우만 만들면 됩니다.
