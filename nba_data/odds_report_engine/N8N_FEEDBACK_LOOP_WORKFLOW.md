# 🔄 n8n Workflow - NBA GraphRAG Feedback Loop

## 워크플로우 개요

```
경기 전 → Event 생성 → AI 예측
경기 후 → BoxScore 수집 → Event 검증 → State 업데이트
다음 경기 → State 조회 → 더 정확한 예측
```

---

## 📋 Workflow 1: Pre-Game (경기 전)

### Trigger: 경기 24시간 전

```
[Cron: Daily 09:00 AM]
→ [Get Today's Games API]
→ [For Each Game]
    ├─→ [Create Event Nodes]
    │   ├─ Injury Impact Event
    │   ├─ Market Signal Event
    │   └─ Lineup Change Event
    │
    ├─→ [Query Team/Player State from Neo4j]
    │   └─ GraphRAG로 State 조회
    │
    ├─→ [Generate AI Council Prediction]
    │   ├─ DeepSeek V3
    │   ├─ Qwen 72B
    │   ├─ Grok 4.1 Fast
    │   ├─ Gemini 2.5 Flash
    │   └─ GPT-4o-mini
    │
    └─→ [Save CouncilPrediction Node to Neo4j]
```

### n8n 노드 구성

```json
{
  "workflow_name": "NBA Pre-Game Analysis",
  "nodes": [
    {
      "type": "Cron",
      "name": "Daily Trigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "0 9 * * *"}]
        }
      }
    },
    {
      "type": "HTTP Request",
      "name": "Get NBA Schedule",
      "parameters": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        "method": "GET"
      }
    },
    {
      "type": "Function",
      "name": "Filter Today's Games",
      "parameters": {
        "functionCode": "return items.filter(game => game.status === 'SCHEDULED')"
      }
    },
    {
      "type": "Neo4j",
      "name": "Query Team State",
      "parameters": {
        "query": "MATCH (ts:TeamState {team_id: $team_id}) RETURN ts"
      }
    },
    {
      "type": "HTTP Request",
      "name": "Call AI Council",
      "parameters": {
        "url": "http://localhost:5000/api/council/analyze",
        "method": "POST",
        "body": {
          "game_id": "={{$json.game_id}}",
          "team_states": "={{$json.team_states}}"
        }
      }
    },
    {
      "type": "Neo4j",
      "name": "Save Events & Prediction",
      "parameters": {
        "query": "CREATE (e:Event {...}), (c:CouncilPrediction {...})"
      }
    }
  ]
}
```

---

## 📋 Workflow 2: Post-Game (경기 후)

### Trigger: 경기 종료 후 30분

```
[Webhook: Game Completed] 또는 [Cron: Every Hour]
→ [Get Completed Games]
→ [For Each Completed Game]
    ├─→ [Fetch BoxScore API]
    │   └─ ESPN BoxScore API
    │
    ├─→ [Create BoxScore Node]
    │   └─ Neo4j에 저장
    │
    ├─→ [Validate Events]
    │   ├─ Injury Impact Event 검증
    │   ├─ Market Signal Event 검증
    │   └─ AI Council Prediction 검증
    │
    └─→ [Update Team/Player State]
        ├─ Regime Confidence 업데이트
        ├─ Injury Resilience 업데이트
        ├─ Market Trust 업데이트
        └─ Player Impact 업데이트
```

### n8n 노드 구성

```json
{
  "workflow_name": "NBA Post-Game Feedback Loop",
  "nodes": [
    {
      "type": "Cron",
      "name": "Hourly Check",
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "30 * * * *"}]
        }
      }
    },
    {
      "type": "Neo4j",
      "name": "Find Completed Games Without BoxScore",
      "parameters": {
        "query": "MATCH (g:Game {status: 'COMPLETED'}) WHERE NOT (g)-[:RESULTED_IN]->(:BoxScore) RETURN g"
      }
    },
    {
      "type": "HTTP Request",
      "name": "Fetch BoxScore",
      "parameters": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={{$json.game_id}}",
        "method": "GET"
      }
    },
    {
      "type": "Function",
      "name": "Parse BoxScore",
      "parameters": {
        "functionCode": `
          const boxScore = {
            game_id: items[0].json.game_id,
            home_score: items[0].json.boxscore.teams.home.statistics.points,
            away_score: items[0].json.boxscore.teams.away.statistics.points,
            margin: items[0].json.boxscore.teams.home.statistics.points - items[0].json.boxscore.teams.away.statistics.points
          };
          return [boxScore];
        `
      }
    },
    {
      "type": "Neo4j",
      "name": "Create BoxScore Node",
      "parameters": {
        "query": "MERGE (g:Game {game_id: $game_id}) CREATE (b:BoxScore {...}) CREATE (g)-[:RESULTED_IN]->(b)"
      }
    },
    {
      "type": "Neo4j",
      "name": "Validate Injury Events",
      "parameters": {
        "query": "MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})... (FEEDBACK_LOOP_QUERIES.cypher 참조)"
      }
    },
    {
      "type": "Neo4j",
      "name": "Update Team State - Regime",
      "parameters": {
        "query": "MATCH (e:Event {game_id: $game_id})... (FEEDBACK_LOOP_QUERIES.cypher 참조)"
      }
    },
    {
      "type": "Neo4j",
      "name": "Update Team State - Injury Resilience",
      "parameters": {
        "query": "MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})... (FEEDBACK_LOOP_QUERIES.cypher 참조)"
      }
    },
    {
      "type": "Neo4j",
      "name": "Update Team State - Market Trust",
      "parameters": {
        "query": "MATCH (e:Event {game_id: $game_id, event_type: 'MARKET_SIGNAL'})... (FEEDBACK_LOOP_QUERIES.cypher 참조)"
      }
    },
    {
      "type": "Function",
      "name": "Log Update Summary",
      "parameters": {
        "functionCode": "console.log('State updated for game:', items[0].json.game_id)"
      }
    }
  ]
}
```

---

## 📋 Workflow 3: Daily Cleanup (매일 정리)

### Trigger: 매일 새벽 3시

```
[Cron: Daily 03:00 AM]
→ [Archive Old Events]
    └─ 7일 이상 된 Event → ArchivedEvent로 이동
→ [Update System Metrics]
    ├─ AI Council 30일 정확도
    ├─ Regime 예측 성공률
    └─ Top Performing Teams
```

---

## 🔧 n8n 설정 가이드

### 1. Neo4j Credential 설정

```javascript
// n8n Credentials > Neo4j
{
  "host": "localhost",
  "port": 7687,
  "user": "neo4j",
  "password": "quickpass123",
  "scheme": "bolt"
}
```

### 2. OpenRouter API Credential

```javascript
// n8n Credentials > HTTP Header Auth
{
  "name": "Authorization",
  "value": "Bearer sk-or-v1-..."
}
```

### 3. Workflow Variables

```javascript
// n8n Workflow Settings > Variables
{
  "NEO4J_URI": "bolt://localhost:7687",
  "ODDS_API_KEY": "b01049f1f29d61c53189799c40d66f69",
  "OPENROUTER_API_KEY": "sk-or-v1-...",
  "ESPN_API_BASE": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
}
```

---

## 📊 Workflow 실행 순서 (실제 예시)

### Day 1 (경기 전날)

```
09:00 AM - Pre-Game Workflow 실행
├─ TOR vs GSW 경기 발견
├─ Event 생성:
│  ├─ INJURY_IMPACT (RJ Barrett OUT, expected: -8.5)
│  └─ MARKET_SIGNAL (Line: GSW -4.5)
├─ Team State 조회:
│  ├─ TOR: DECLINE (0.87 conf)
│  └─ GSW: ROAD_DOMINANCE (0.91 conf)
└─ AI Council 예측: 3/5 BET
```

### Day 1 (경기 후)

```
11:30 PM - Post-Game Workflow 실행
├─ BoxScore 수집:
│  ├─ TOR 102 - 115 GSW
│  └─ Margin: -13
├─ Event 검증:
│  ├─ INJURY_IMPACT: SUCCESS (예측 -8.5, 실제 -13)
│  └─ MARKET_SIGNAL: SUCCESS (GSW covered)
└─ State 업데이트:
   ├─ TOR regime_confidence: 0.87 → 0.89 (예측 성공)
   ├─ TOR injury_resilience: MEDIUM → LOW (큰 패배)
   └─ GSW regime_confidence: 0.91 → 0.93 (연속 성공)
```

### Day 2 (다음 경기)

```
09:00 AM - Pre-Game Workflow 실행 (TOR vs BOS)
├─ Team State 조회 (업데이트된 값 사용):
│  ├─ TOR: DECLINE (0.89 conf, Resilience: LOW)
│  └─ BOS: DOMINANCE (0.85 conf)
├─ AI Council 예측: 4/5 BET (이전보다 더 확신)
│  └─ "TOR의 injury_resilience가 LOW로 떨어졌고, regime_confidence가 올라갔지만 여전히 DECLINE"
└─ 더 정확한 예측!
```

---

## 🎯 핵심 원칙

1. **Event는 일회용** - 검증 후 Archive
2. **State는 누적** - EMA로 smooth update
3. **BoxScore는 채점기** - Event와 AI 예측 검증
4. **다음 경기는 State만 조회** - Event 조회 안 함
5. **자기 학습** - 틀릴수록 State가 정확해짐

---

## 📝 n8n Workflow JSON Export

실제 n8n에서 import 가능한 JSON은 별도 파일로 생성:
- `n8n_pre_game_workflow.json`
- `n8n_post_game_workflow.json`
- `n8n_daily_cleanup_workflow.json`

---

## 🚀 다음 단계

1. n8n 설치 및 실행
2. Neo4j 연결 설정
3. Workflow Import
4. Test Run (TOR vs GSW 샘플 데이터)
5. Production 배포

---

**이게 바로 "오답 노트 자동 생성" 시스템입니다!** 🎯
