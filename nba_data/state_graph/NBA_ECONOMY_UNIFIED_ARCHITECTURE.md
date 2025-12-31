# NBA & Economy 통합 아키텍처

**작성일**: 2025-12-26
**목적**: NBA와 경제레짐 시스템의 공통 로직 통합

---

## 🎯 통합 배경

### 공통 패턴 발견

**NBA Real-time Pipeline**:
```
X Search → 화이트리스트 체크 → Grok 정규화 → Neo4j 저장
```

**Economy Event Pipeline**:
```
X Search → 화이트리스트 체크 → Gemini 분석 → Neo4j 저장
```

**공통 요소**:
1. ✅ X (Twitter) API 모니터링
2. ✅ 화이트리스트 Tier 검증
3. ✅ OpenRouter를 통한 LLM 분석
4. ✅ Neo4j 그래프 저장
5. ✅ n8n 워크플로우 오케스트레이션
6. ✅ 환경변수 관리 (.env)

---

## 📁 공통 모듈 구조

### 1. 환경변수 통합

**위치**: `/Users/js/g9/nba_data/.env.unified`

```bash
# ========================================
# 🔥 G9 UNIFIED ENV (NBA + Economy)
# ========================================

# ----------------------------------------
# OpenRouter (공통 LLM 인프라)
# ----------------------------------------
OPENROUTER_API_KEY=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

# ----------------------------------------
# X (Twitter) API
# ----------------------------------------
# xAI Native API (X Search용)
XAI_API_KEY=your_xai_key_here

# 또는 Twitter OAuth2
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# ----------------------------------------
# Neo4j (공통 그래프 DB)
# ----------------------------------------
# NBA용
NEO4J_NBA_URI=bolt://localhost:7687
NEO4J_NBA_USER=neo4j
NEO4J_NBA_PASSWORD=your_nba_password

# Economy용
NEO4J_ECONOMY_URI=bolt://localhost:7475
NEO4J_ECONOMY_USER=neo4j
NEO4J_ECONOMY_PASSWORD=your_economy_password

# ----------------------------------------
# n8n
# ----------------------------------------
N8N_HOST=localhost:5678
N8N_WEBHOOK_URL=http://localhost:5678/webhook

# ----------------------------------------
# LLM 모델 설정
# ----------------------------------------
# NBA: Grok (빠르고 정확한 정규화)
NBA_LLM_MODEL=x-ai/grok-4.1-fast

# Economy: Gemini (저렴하고 안정적)
ECONOMY_LLM_MODEL=google/gemini-2.0-flash-001

# Reddit (심층 분석용)
REDDIT_LLM_MODEL=qwen/qwen2.5-vl-72b-instruct

# ----------------------------------------
# 기타 API
# ----------------------------------------
# Reddit
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=NBA-Economy-Bot/1.0

# Pusher (실시간 알림)
PUSHER_APP_ID=your_pusher_app_id
PUSHER_KEY=your_pusher_key
PUSHER_SECRET=your_pusher_secret
PUSHER_CLUSTER=us2

# ----------------------------------------
# 기존 API 키들 (g9_core_export)
# ----------------------------------------
FRED_API_KEY=60b84364c9e7b299ea792773b9b63b0a
KOSIS_API_KEY=MGE1YjQyNjRkYmExODdlMGY2N2IyYzRkMTZlNDhhN2Y=
BOK_API_KEY=SN05WTFXN2534FECUO8T
GEMINI_API_KEY=AIzaSyAYbHt6sbb4MuFgJa_uMdJY_R4zfYdQdMk
DASHSCOPE_API_KEY=sk-eaa53282392f489bba4af8c2743a9317

# ----------------------------------------
# Logging
# ----------------------------------------
LOG_LEVEL=INFO
BASE_DIR=/Users/js/g9
```

---

### 2. 공통 n8n 함수 모듈

**위치**: `/Users/js/g9/nba_data/state_graph/shared/n8n_functions.js`

#### 2-1. 화이트리스트 체크 함수

```javascript
/**
 * 화이트리스트 Tier 검증 (NBA + Economy 공통)
 *
 * @param {string} username - X 사용자명
 * @param {string} domain - "nba" | "economy"
 * @returns {object|null} - {tier, username} 또는 null
 */
function checkWhitelist(username, domain) {
  const WHITELISTS = {
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
  };

  const whitelist = WHITELISTS[domain];
  if (!whitelist) return null;

  const normalizedUsername = username.toLowerCase();

  for (const [tier, accounts] of Object.entries(whitelist)) {
    if (accounts.map(a => a.toLowerCase()).includes(normalizedUsername)) {
      return {
        tier: parseInt(tier.replace('tier', '')),
        username: '@' + username
      };
    }
  }

  return null;
}

// n8n에서 사용
const username = $input.item.json.user.screen_name;
const domain = $node["Config"].json.domain; // "nba" or "economy"

const whitelistResult = checkWhitelist(username, domain);

if (!whitelistResult) {
  return []; // 버림
}

return [{
  json: {
    ...$input.item.json,
    source_tier: whitelistResult.tier,
    source_account: whitelistResult.username
  }
}];
```

#### 2-2. OpenRouter AI 호출 함수

```javascript
/**
 * OpenRouter를 통한 LLM 분석 (공통 함수)
 *
 * @param {string} model - LLM 모델명
 * @param {string} systemPrompt - 시스템 프롬프트
 * @param {string} userContent - 사용자 입력
 * @param {number} temperature - 온도 (기본 0.1)
 * @param {number} maxTokens - 최대 토큰 (기본 1000)
 * @returns {object} - AI 응답 JSON
 */
async function callOpenRouterLLM({
  model,
  systemPrompt,
  userContent,
  temperature = 0.1,
  maxTokens = 1000
}) {
  const OPENROUTER_API_KEY = $env.OPENROUTER_API_KEY;

  const response = await $http.request({
    method: 'POST',
    url: 'https://openrouter.ai/api/v1/chat/completions',
    headers: {
      'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
      'HTTP-Referer': 'http://localhost:5678',
      'Content-Type': 'application/json'
    },
    body: {
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userContent }
      ],
      temperature,
      max_tokens: maxTokens
    }
  });

  return response.data;
}

// NBA 사용 예시
const nbaAnalysis = await callOpenRouterLLM({
  model: 'x-ai/grok-4.1-fast',
  systemPrompt: 'You are an NBA event normalizer...',
  userContent: $json.text,
  temperature: 0.1,
  maxTokens: 500
});

// Economy 사용 예시
const economyAnalysis = await callOpenRouterLLM({
  model: 'google/gemini-2.0-flash-001',
  systemPrompt: '당신은 경제 이벤트 분류 전문가입니다...',
  userContent: `출처: ${$json.source_account}\n트윗: ${$json.text}`,
  temperature: 0.1,
  maxTokens: 1000
});
```

#### 2-3. JSON 파싱 함수 (공통)

```javascript
/**
 * AI 응답에서 JSON 추출 및 파싱
 *
 * @param {string} aiResponse - AI 응답 텍스트
 * @returns {object} - 파싱된 JSON 객체
 */
function parseAIResponse(aiResponse) {
  let jsonStr = aiResponse.trim();

  // 코드 블록 제거
  if (jsonStr.includes('```json')) {
    jsonStr = jsonStr.split('```json')[1].split('```')[0].trim();
  } else if (jsonStr.includes('```')) {
    jsonStr = jsonStr.split('```')[1].split('```')[0].trim();
  }

  try {
    return JSON.parse(jsonStr);
  } catch (error) {
    console.error('JSON 파싱 실패:', error);
    throw new Error(`Invalid JSON from AI: ${jsonStr.substring(0, 100)}...`);
  }
}

// n8n에서 사용
const aiResponse = $input.item.json.choices[0].message.content;
const parsed = parseAIResponse(aiResponse);

return [{ json: parsed }];
```

---

### 3. 공통 Neo4j 저장 로직

**위치**: `/Users/js/g9/nba_data/state_graph/shared/neo4j_utils.py`

```python
import os
from neo4j import GraphDatabase
from datetime import datetime
from typing import Dict, Any, Literal

class UnifiedNeo4jClient:
    """
    NBA와 Economy 시스템을 위한 통합 Neo4j 클라이언트
    """

    def __init__(self, domain: Literal["nba", "economy"]):
        """
        Args:
            domain: "nba" 또는 "economy"
        """
        self.domain = domain

        # 도메인별 Neo4j 연결 정보
        if domain == "nba":
            uri = os.getenv("NEO4J_NBA_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_NBA_USER", "neo4j")
            password = os.getenv("NEO4J_NBA_PASSWORD")
        else:  # economy
            uri = os.getenv("NEO4J_ECONOMY_URI", "bolt://localhost:7475")
            user = os.getenv("NEO4J_ECONOMY_USER", "neo4j")
            password = os.getenv("NEO4J_ECONOMY_PASSWORD")

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def store_event(self, event_data: Dict[str, Any]) -> str:
        """
        공통 이벤트 저장 로직

        Args:
            event_data: 이벤트 데이터 딕셔너리

        Returns:
            event_id: 생성된 이벤트 ID
        """
        with self.driver.session() as session:
            if self.domain == "nba":
                return self._store_nba_event(session, event_data)
            else:
                return self._store_economy_event(session, event_data)

    def _store_nba_event(self, session, event_data: Dict[str, Any]) -> str:
        """NBA 이벤트 저장"""
        result = session.run("""
            CREATE (e:Event:NBAEvent {
                event_id: $event_id,
                timestamp: datetime($timestamp),
                event_type: $event_type,
                player: $player,
                team: $team,
                status: $status,
                reason: $reason,
                tweet_id: $tweet_id,
                tweet_url: $tweet_url,
                source_account: $source_account,
                source_tier: $source_tier,
                confidence: $confidence
            })

            WITH e
            OPTIONAL MATCH (p:Player {name: $player})
            FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                MERGE (p)-[:HAS_EVENT]->(e)
            )

            WITH e
            OPTIONAL MATCH (t:Team {abbreviation: $team})
            FOREACH (_ IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END |
                MERGE (t)-[:HAS_EVENT]->(e)
            )

            RETURN e.event_id AS event_id
        """, **event_data)

        return result.single()["event_id"]

    def _store_economy_event(self, session, event_data: Dict[str, Any]) -> str:
        """경제 이벤트 저장"""
        result = session.run("""
            CREATE (e:Event:EconomicEvent {
                event_id: $event_id,
                timestamp: datetime($timestamp),
                type: $type,
                subtype: $subtype,
                magnitude: $magnitude,
                direction: $direction,
                affected_factors: $affected_factors,
                confidence: $confidence,
                title: $title,
                description: $description,
                keywords: $keywords,
                tweet_id: $tweet_id,
                tweet_url: $tweet_url,
                source_account: $source_account,
                source_tier: $source_tier
            })

            WITH e
            UNWIND $affected_factors AS factor_name
            MATCH (f:Factor {name: factor_name})
            MERGE (e)-[:AFFECTS]->(f)

            RETURN e.event_id AS event_id
        """, **event_data)

        return result.single()["event_id"]

    def close(self):
        """Neo4j 연결 종료"""
        self.driver.close()

# 사용 예시
if __name__ == "__main__":
    # NBA 이벤트 저장
    nba_client = UnifiedNeo4jClient("nba")
    nba_event = {
        "event_id": "evt_nba_123",
        "timestamp": datetime.now().isoformat(),
        "event_type": "injury_report",
        "player": "LeBron James",
        "team": "LAL",
        "status": "OUT",
        "reason": "ankle",
        "tweet_id": "1234567890",
        "tweet_url": "https://twitter.com/ShamsCharania/status/1234567890",
        "source_account": "@ShamsCharania",
        "source_tier": 2,
        "confidence": 0.95
    }
    nba_client.store_event(nba_event)
    nba_client.close()

    # Economy 이벤트 저장
    economy_client = UnifiedNeo4jClient("economy")
    economy_event = {
        "event_id": "evt_economy_456",
        "timestamp": datetime.now().isoformat(),
        "type": "PolicyChange",
        "subtype": "Rate Hike",
        "magnitude": 0.25,
        "direction": "up",
        "affected_factors": ["Interest Rate", "Dollar Strength"],
        "confidence": 0.95,
        "title": "Fed 금리 인상 25bp",
        "description": "연준이 기준금리를 25bp 인상하며...",
        "keywords": ["Fed", "금리인상", "25bp"],
        "tweet_id": "9876543210",
        "tweet_url": "https://twitter.com/federalreserve/status/9876543210",
        "source_account": "@federalreserve",
        "source_tier": 1
    }
    economy_client.store_event(economy_event)
    economy_client.close()
```

---

## 🔄 통합 워크플로우

### n8n에서 공통 함수 사용

**NBA 워크플로우**:
```javascript
// Node 1: X Search
// ...

// Node 2: 화이트리스트 체크 (공통 함수 사용)
const whitelistResult = checkWhitelist($json.user.screen_name, 'nba');
if (!whitelistResult) return [];

// Node 3: Grok 분석 (공통 함수 사용)
const analysis = await callOpenRouterLLM({
  model: $env.NBA_LLM_MODEL,
  systemPrompt: 'NBA event normalizer...',
  userContent: $json.text
});

// Node 4: JSON 파싱 (공통 함수 사용)
const parsed = parseAIResponse(analysis.choices[0].message.content);

// Node 5: Neo4j 저장 (Python 스크립트 호출)
// Exec: python3 shared/neo4j_utils.py --domain nba --data '{...}'
```

**Economy 워크플로우**:
```javascript
// Node 1: X Search
// ...

// Node 2: 화이트리스트 체크 (동일한 공통 함수)
const whitelistResult = checkWhitelist($json.user.screen_name, 'economy');
if (!whitelistResult) return [];

// Node 3: Gemini 분석 (공통 함수, 다른 모델)
const analysis = await callOpenRouterLLM({
  model: $env.ECONOMY_LLM_MODEL,
  systemPrompt: '경제 이벤트 분류 전문가...',
  userContent: $json.text
});

// Node 4: JSON 파싱 (동일한 공통 함수)
const parsed = parseAIResponse(analysis.choices[0].message.content);

// Node 5: Neo4j 저장 (동일한 Python 스크립트, 다른 도메인)
// Exec: python3 shared/neo4j_utils.py --domain economy --data '{...}'
```

---

## 📊 비용 분석

### 통합 후 월간 비용

| 서비스 | NBA | Economy | 합계 |
|--------|-----|---------|------|
| X Search (xAI) | $0.50 | $0.20 | **$0.70** |
| OpenRouter (Grok/Gemini) | $0.19 | $0.24 | **$0.43** |
| Neo4j (Self-hosted) | $0.00 | $0.00 | **$0.00** |
| **총합** | $0.69 | $0.44 | **$1.13/월** |

**절감 효과**:
- 공통 함수 재사용 → 개발 시간 50% 절감
- 통합 환경변수 → 관리 복잡도 감소
- 단일 n8n 인스턴스 → 인프라 비용 절감

---

## 🚀 다음 단계

### 1. 공통 모듈 생성
```bash
mkdir -p /Users/js/g9/nba_data/state_graph/shared
touch shared/n8n_functions.js
touch shared/neo4j_utils.py
touch shared/README.md
```

### 2. 환경변수 통합
```bash
cp ../g9_core_export/.env .env.unified
# NBA와 Economy 환경변수 병합
```

### 3. 기존 워크플로우 마이그레이션
```bash
# NBA 워크플로우 업데이트
# Economy 워크플로우 업데이트
# 공통 함수로 교체
```

### 4. 테스트
```bash
# NBA 워크플로우 테스트
# Economy 워크플로우 테스트
# Neo4j 저장 확인
```

---

## ✅ 통합 완료 체크리스트

- [ ] `shared/` 디렉토리 생성
- [ ] `shared/n8n_functions.js` 작성
- [ ] `shared/neo4j_utils.py` 작성
- [ ] `.env.unified` 생성 및 병합
- [ ] NBA 워크플로우 마이그레이션
- [ ] Economy 워크플로우 마이그레이션
- [ ] 통합 테스트 실행
- [ ] 문서화 업데이트

---

**작성자**: Claude Code
**버전**: v1.0
**상태**: 설계 완료, 구현 대기
