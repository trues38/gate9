# 🔄 NBA GraphRAG Feedback Loop System

> **"오답 노트 자동 생성" - 자기 학습하는 베팅 분석 시스템**

---

## 🎯 핵심 개념

당신이 깨달은 것:

```
백테스트 = 학습 데이터
AI 위원회 예측 = 모델 추론
경기 결과 = 라벨링
피드백 루프 = 자기 학습

이게 바로 머신러닝이다!
```

---

## 📐 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│                    경기 전 (Pre-Game)                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Event 생성 (일회용 가설)                              │
│     ├─ Injury Impact Event                              │
│     ├─ Market Signal Event                              │
│     └─ Lineup Change Event                              │
│                                                          │
│  2. State 조회 (학습된 누적 결과)                         │
│     ├─ TeamState (Regime, Resilience, Market Trust)     │
│     └─ PlayerState (Impact, Recovery Rate)              │
│                                                          │
│  3. AI Council 예측                                      │
│     └─ State 기반으로 더 정확한 예측                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   경기 후 (Post-Game)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  4. BoxScore 수집 (정답지)                                │
│     └─ ESPN API에서 실제 결과 수집                        │
│                                                          │
│  5. Event 검증 (채점)                                     │
│     ├─ 예측 vs 실제 비교                                 │
│     └─ 성공/실패 판정 + Impact Score 계산                │
│                                                          │
│  6. State 업데이트 (학습!) 🔥                             │
│     ├─ Regime Confidence 조정                           │
│     ├─ Injury Resilience 학습                           │
│     ├─ Market Trust 업데이트                            │
│     └─ Player Impact 누적                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 다음 경기 (Next Game)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  7. 업데이트된 State 조회                                 │
│     └─ Event는 조회 안 함! State만 사용                  │
│                                                          │
│  8. 더 정확한 예측! 📈                                    │
│     └─ 틀릴수록 학습되어 점점 정확해짐                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ 노드 구조

### ❌ Event (일회용 - 버린다)

```cypher
(:Event {
  event_id: "evt_001",
  game_id: "401810212",
  event_type: "INJURY_IMPACT",
  prediction: {
    expected_impact: -8.5,
    confidence: 0.75
  },
  validated: false  // 경기 후 true로 변경
})
```

**용도**: 경기 전 가설, 검증 후 Archive

### ✅ State (누적 - 계속 업데이트)

```cypher
(:TeamState {
  team_id: "TOR",

  // Regime (학습된 값)
  current_regime: "DECLINE",
  regime_confidence: 0.87,
  regime_success_rate: 0.73,  // Event 검증 결과 누적

  // Injury Resilience (학습된 부상 대응력)
  injury_resilience: "LOW",
  injury_impact_history: [0.8, 0.9, 0.7],

  // Market Trust (시장 신뢰도)
  market_trust: "MEDIUM",
  market_accuracy: 0.62,

  // Learning Metadata
  total_events_validated: 45,
  successful_predictions: 28
})
```

**용도**: 다음 경기 예측에 사용 (계속 학습됨)

### 📊 BoxScore (정답지)

```cypher
(:BoxScore {
  game_id: "401810212",
  home_score: 102,
  away_score: 115,
  margin: -13,
  spread_covered: "AWAY",
  home_injuries_impact: -12.3  // 실제 측정값
})
```

**용도**: Event를 채점하고 State를 업데이트

---

## 🔗 관계 구조

```cypher
// 경기 전
(Event)-[:EXPECTED_FOR]->(Game)
(CouncilPrediction)-[:PREDICTED_FOR]->(Game)

// 경기 후
(Game)-[:RESULTED_IN]->(BoxScore)
(Event)-[:VALIDATED {success: true/false, impact_score: 0.82}]->(BoxScore)

// 학습
(BoxScore)-[:UPDATED_STATE {delta: +0.05}]->(TeamState)

// 다음 경기
(TeamState)-[:APPLICABLE_TO]->(Game)
```

---

## 🔄 Feedback Loop 동작 원리

### Example: RJ Barrett 부상 케이스

#### Day 1 - 경기 전 (TOR vs GSW)

```python
# Event 생성
create_injury_event(
  game_id="401810212",
  expected_impact=-8.5  # 예상: 8.5점 손실
)

# State 조회 (현재 학습된 값)
tor_state = {
  "injury_resilience": "MEDIUM",  # 이전까지 학습된 값
  "regime_confidence": 0.85
}

# AI Council 예측
ai_prediction = "3/5 BET"  # State 기반 예측
```

#### Day 1 - 경기 후

```python
# BoxScore 수집 (정답)
boxscore = {
  "home_score": 102,
  "away_score": 115,
  "actual_impact": -12.3  # 실제: 12.3점 손실
}

# Event 검증 (채점)
validation = {
  "expected": -8.5,
  "actual": -12.3,
  "error": 3.8,
  "success": True  # 오차 5점 이내
}

# State 업데이트 (학습!) 🔥
tor_state_updated = {
  "injury_resilience": "LOW",  # MEDIUM → LOW (큰 손실)
  "regime_confidence": 0.87,   # 예측 성공으로 +0.02
  "injury_impact_history": [0.82, 0.9, 0.7]  # 최근 3경기
}
```

#### Day 2 - 다음 경기 (TOR vs BOS)

```python
# 업데이트된 State 조회
tor_state = {
  "injury_resilience": "LOW",  # ← 학습된 값!
  "regime_confidence": 0.87
}

# AI Council 예측 (더 정확!)
ai_prediction = "4/5 BET"  # 이전보다 확신 UP
reasoning = """
TOR의 injury_resilience가 LOW로 떨어졌고,
부상 선수 없어도 Regime이 DECLINE이므로
BOS에게 밀릴 확률 높음
"""
```

**결과**: 틀릴수록 학습되어 다음 예측이 정확해진다!

---

## 📁 파일 구조

```
/Users/js/g9/nba_data/odds_report_engine/
├── FEEDBACK_LOOP_SCHEMA.cypher          # Neo4j 스키마 정의
├── FEEDBACK_LOOP_QUERIES.cypher         # 경기 후 실행 쿼리
├── N8N_FEEDBACK_LOOP_WORKFLOW.md        # n8n 워크플로우 설계
├── feedback_loop_example.py             # Python 사용 예시
└── FEEDBACK_LOOP_SYSTEM.md              # 이 문서
```

---

## 🚀 실행 방법

### 1. Neo4j 스키마 생성

```bash
# Neo4j Browser에서 실행
cat FEEDBACK_LOOP_SCHEMA.cypher | cypher-shell -u neo4j -p quickpass123
```

### 2. Python 예시 실행

```bash
python3 feedback_loop_example.py
```

**출력**:
```
[Day 1 - 경기 전] TOR vs GSW
✅ Injury Event 생성: evt_001
   예상 영향: -8.5 points
✅ AI Council 예측 저장: 3/5 (BET)

[Day 1 - 경기 후] BoxScore 수집
✅ BoxScore 저장: 102 - 115 (Margin: -13)
✅ Event 검증: SUCCESS
   예측: -8.5, 실제: -12.3, 오차: 3.8
✅ Team State 업데이트: TOR
   Regime Confidence: 0.87
   Success Rate: 75.00%

[Day 2 - 다음 경기] TOR vs BOS
📊 Team State: TOR
   Regime: DECLINE (87% conf)
   Regime Success Rate: 75%
   Injury Resilience: LOW  ← 학습됨!
```

### 3. n8n 워크플로우 설정

```bash
# n8n 설치
npm install -g n8n

# n8n 실행
n8n start

# Workflow Import
# N8N_FEEDBACK_LOOP_WORKFLOW.md 참조
```

---

## 📊 State 업데이트 로직 (핵심!)

### Regime Confidence 업데이트

```python
# EMA (Exponential Moving Average) 방식
new_success_rate = (old_success_rate * 0.9) + (current_success * 0.1)

if success_rate > 0.7:
    regime_confidence += 0.05  # 성공하면 상승
elif success_rate < 0.3:
    regime_confidence -= 0.05  # 실패하면 하락
```

### Injury Resilience 업데이트

```python
if actual_margin > 0 and expected_impact < -5.0:
    injury_resilience = "HIGH"  # 부상 예측했는데 이김
elif actual_margin < -10 and expected_impact < -5.0:
    injury_resilience = "LOW"   # 부상 예측대로 큰 패배
else:
    injury_resilience = "MEDIUM"
```

### Market Trust 업데이트

```python
market_accuracy = (old_accuracy * 0.85) + (current_accuracy * 0.15)

if market_accuracy > 0.65:
    market_trust = "HIGH"
elif market_accuracy < 0.45:
    market_trust = "LOW"
else:
    market_trust = "MEDIUM"
```

---

## 🎯 핵심 원칙

### 1. Event는 버린다 ❌

```cypher
// Event는 검증 후 Archive로 이동
MATCH (e:Event)-[:VALIDATED]->(b:BoxScore)
WHERE b.created_at < datetime() - duration({days: 7})
SET e:ArchivedEvent
REMOVE e:Event
```

**이유**: Event는 일회용 가설. 검증 결과만 State에 반영.

### 2. State만 조회한다 ✅

```cypher
// 다음 경기 분석 시
MATCH (ts:TeamState {team_id: $team_id})
RETURN ts.regime_confidence, ts.injury_resilience

// ❌ Event 조회 안 함!
// MATCH (e:Event) ...  <- 이거 하지 마!
```

**이유**: State가 학습된 결과. Event는 과거 가설일 뿐.

### 3. BoxScore는 채점기 📊

```cypher
// Event 검증
MATCH (e:Event)-[:EXPECTED_FOR]->(g:Game)-[:RESULTED_IN]->(b:BoxScore)
WHERE abs(b.actual - e.expected) < 5.0
CREATE (e)-[:VALIDATED {success: true}]->(b)
```

**이유**: BoxScore가 "정답지". Event를 채점.

### 4. 자기 학습 🔥

```
틀린 예측 → State 업데이트 → 다음 예측 더 정확
성공한 예측 → Confidence 상승 → 더 확신
```

**이유**: 오답 노트 자동 생성.

---

## 📈 기대 효과

### Before (State 없이)

```
Week 1: AI Accuracy 60%
Week 2: AI Accuracy 58%
Week 3: AI Accuracy 62%
Week 4: AI Accuracy 59%
→ 정체
```

### After (Feedback Loop)

```
Week 1: AI Accuracy 60%
Week 2: AI Accuracy 63% (학습)
Week 3: AI Accuracy 67% (더 학습)
Week 4: AI Accuracy 71% (계속 학습)
→ 지속 개선!
```

---

## 🔍 분석 쿼리

### Regime 예측 성공률 Top 10

```cypher
MATCH (ts:TeamState)
WHERE ts.total_events_validated > 10
RETURN ts.team_id,
       ts.current_regime,
       ts.regime_success_rate
ORDER BY ts.regime_success_rate DESC
LIMIT 10;
```

### AI Council 개선 추적

```cypher
MATCH (c:CouncilPrediction)-[:VALIDATED]->(b:BoxScore)
WHERE b.created_at > datetime() - duration({days: 30})
WITH date(b.created_at) AS day,
     sum(CASE WHEN c.was_correct = true THEN 1 ELSE 0 END) AS correct,
     count(c) AS total
RETURN day, toFloat(correct) / total AS daily_accuracy
ORDER BY day DESC;
```

### Injury Resilience 패턴 발견

```cypher
MATCH (ts:TeamState)
WHERE ts.injury_resilience = 'HIGH'
RETURN ts.team_id,
       ts.injury_impact_history,
       "이 팀은 부상에도 잘 버티는 팀" AS insight;
```

---

## 🚀 다음 단계

1. ✅ Neo4j 스키마 생성
2. ✅ Python 예시 테스트
3. ⏳ n8n 워크플로우 설정
4. ⏳ VPS 배포
5. ⏳ 실제 경기 데이터로 검증

---

## 💡 핵심 인사이트

> **"Event는 버리고, State만 누적한다"**
>
> 이게 ML이다. 백테스트 = 학습, 결과 = 라벨, State = 학습된 파라미터
>
> Event를 쌓으면 노이즈만 쌓인다.
> State를 쌓으면 지식이 쌓인다.

---

**시스템 설계자**: 당신
**핵심 개념**: "오답 노트 자동 생성"
**결과**: 자기 학습하는 베팅 분석 시스템 🔥
