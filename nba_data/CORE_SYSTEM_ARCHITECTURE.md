# G9 Core Architecture (VPS + Local)

## 🏗️ 시스템 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    G9 NBA Intelligence Platform                 │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐          ┌──────────────────────┐
│   LOCAL (맥북)       │          │     VPS (N8N)        │
│   daily_automation   │          │   실시간 파이프라인   │
└──────────────────────┘          └──────────────────────┘
          │                                │
          │                                │
    ✅ 매일 09:00 UTC               ✅ 5PM-11PM ET (NBA)
          │                         ✅ 9AM UTC (Economy)
          │                                │
    정량 계산:                        실시간 감지:
    ├─ PlayerBoxScore                ├─ Injury Event
    ├─ PlayerRecentForm              ├─ Lineup Change
    ├─ RefereeStats                  ├─ Referee Assignment
    ├─ TeamStrength                  ├─ Trade Event
    ├─ CoachStats                    ├─ Economic Event
    ├─ RosterStats                   └─ Odds Movement
    └─ PLAYS_FOR relations               (사용자 추가)
          │                                │
          │                                │
          └────────────────┬────────────────┘
                           │
                           ↓
                    ┌──────────────┐
                    │    Neo4j     │
                    │   그래프DB   │
                    └──────────────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
                ↓          ↓          ↓
         ┌────────────────────────┐
         │  실시간 분석 엔진       │
         │ (Analysis Engine)      │
         │                        │
         │ ① Event 감지 시        │
         │    Graph 재계산        │
         │                        │
         │ ② 영향도 분석          │
         │    (Player/Team/Game) │
         │                        │
         │ ③ Confidence 계산      │
         └────────────────────────┘
                │
                ↓
         ┌──────────────────────────┐
         │   Report Generation      │
         │   (본석 레포트 생성)     │
         │                          │
         │ ① Situation Analysis     │
         │ ② Quantitative Insight   │
         │ ③ Market Intelligence    │
         │    (배당 - 사용자 추가)  │
         │ ④ Actionable Strategy    │
         └──────────────────────────┘
                │
                ↓
         ┌──────────────────────┐
         │   Output             │
         ├──────────────────────┤
         │ • JSON Report        │
         │ • HTML Dashboard     │
         │ • CSV Analytics      │
         │ • Slack Alert        │
         └──────────────────────┘
```

---

## 📊 데이터 계층

### Layer 1: 기본 정보 (Static)
```
Player (653명)
├─ 25개 속성
└─ 자동 업데이트: 매일 09:00 UTC

Coach (24명)
├─ 12개 속성 (스타일, 신뢰도)
└─ 자동 업데이트: 매일 09:00 UTC

Referee (85명)
├─ RefereeStats (3속성)
└─ 자동 업데이트: 매일 09:00 UTC

Team (30팀)
├─ 2개 기본 속성 (name, abbr)
└─ 관계로부터 정량 데이터
```

### Layer 2: 경기 데이터 (Daily)
```
GameState (2,249경기)
├─ 점수, 휴식일, 심판
└─ 자동 수집: 매일 09:00 UTC

PlayerBoxScore (14,140개)
├─ 경기별 선수 성적
└─ 자동 수집: 매일 09:00 UTC

RosterStats (30개팀)
├─ 팀 평균 통계
└─ 자동 계산: 매일 09:00 UTC
```

### Layer 3: 계산된 통계 (Derived)
```
PlayerRecentForm (1,374개)
├─ 선수 3시즌 최근 성적
└─ 자동 계산: 매일 09:00 UTC

RefereeStats (79명)
├─ 심판 경기 수 및 통계
└─ 자동 계산: 매일 09:00 UTC

TeamStrength (30개팀)
├─ 팀 강도 지수
└─ 자동 계산: 매일 09:00 UTC

CoachStats (~60명)
├─ 감독 통계
└─ 자동 계산: 매일 09:00 UTC
```

### Layer 4: 실시간 이벤트 (Dynamic - VPS)
```
NBAEvent (실시간)
├─ Injury: Player -[INJURY]-> InjuryEvent
├─ Lineup: Team -[LINEUP_CHANGE]-> LineupEvent
├─ Referee: Game -[UPDATED_REFEREE]-> Referee
└─ Trade: Player -[TRADED]-> Team

EconomicEvent (일일)
├─ Market: EconomicEvent -[INFLUENCES]-> Team
├─ Policy: EconomicEvent -[IMPACTS]-> Player
└─ Macro: EconomicEvent -[AFFECTS]-> Game

OddsEvent (실시간 - 사용자 추가)
├─ MoneylineOdds
├─ SpreadOdds
├─ TotalOdds
└─ PlayerPropOdds
```

### Layer 5: 분석된 인사이트 (Analysis)
```
InfluenceFactors
├─ NBAEvent + EconomicEvent 교집합
├─ Odds Movement 분석
└─ Market Sentiment

GamePrediction (경기별)
├─ 우리의 예측
├─ 신뢰도 (confidence)
└─ 변수 추적

Report
├─ 실시간 상황 분석
├─ 정량적 근거
└─ 실행 전략
```

---

## 🔄 데이터 흐름 (실제 시나리오)

### 시나리오: "LeBron OUT 발표" (경기 1시간 전)

**T=0분: VPS에서 감지**
```
Breaking: LeBron James (ankle) OUT
↓
NBAEvent 노드 생성:
{
  event_id: "nba_20251226_001"
  type: "injury"
  player: "LeBron James"
  team: "LAL"
  status: "OUT"
  reason: "right ankle"
  confidence: 0.99
  timestamp: 2025-12-26T19:00:00Z
}
```

**T=1분: 우리의 Graph 자동 재계산**
```
① Player 영향도 분석:
   LeBron 제거 → 15.3 pts, 5.8 reb 손실

② Team 강도 재계산:
   LAL TeamStrength: 82.5 → 73.8 (-8.7)

③ 경기 영향도:
   LAL vs GSW 승률
   Before: 55% (LAL) vs 45% (GSW)
   After:  42% (LAL) vs 58% (GSW)

④ Related 선수 영향:
   - AD: 리바운드 부담 증가 (+2.1 reb)
   - Rui: 공격 분담 증가 (+3.2 pts)

⑤ Coach 전술 변화:
   - 중거리 의존도 증가
   - 빠른 템포 감소
```

**T=2분: 실시간 분석 리포트 생성**
```
SITUATION ANALYSIS:
├─ Event: LeBron James ruled OUT
├─ Impact Level: CRITICAL
└─ Updated Probability: LAL 42% → GSW 58%

QUANTITATIVE INSIGHT:
├─ Team Strength Change: -8.7 points
├─ Player Absence Impact: 15.3 points
└─ Confidence: 94% (based on historical data)

MARKET INTELLIGENCE (당신이 추가할 부분):
├─ Odds Before: LAL -4.5
├─ Odds After: LAL -3.0
├─ Market vs Our Analysis:
│  ├─ Market: 52% (LAL)
│  └─ Our Model: 42% (LAL)
│  → 10% Discrepancy = Opportunity
└─ Betting Pool Sentiment: Still optimistic on LAL

ACTIONABLE STRATEGY:
├─ Primary: GSW +3.0 (better value)
├─ Secondary: GSW Spread Bet
└─ Watch: How market moves next 30 minutes
```

**T=5분: 시장 반응 추적**
```
LAL Spread Movement:
-4.5 → -4.0 → -3.5 → -3.0
(배팅 풀이 LAL에서 빠져나감)

우리의 분석이 시장을 3-5분 선행함
→ Edge 감지 가능
```

---

## 🎯 세 가지 핵심 강점

### 1️⃣ 실시간 변수 감지
```
VPS가 Event 감지 (1분)
↓
우리 Graph가 즉시 재계산 (2분)
↓
시장이 반응 (10-15분)

우리가 시장을 10배 먼저 알아낸다!
```

### 2️⃣ 깊은 그래프 분석
```
Event: "LeBron OUT"

시장의 반응:
└─ 단순히 LAL 강도 감소만 생각

우리의 분석:
├─ LeBron의 정확한 영향도 (15.3pts)
├─ AD, Rui 등 다른 선수 영향도
├─ Coach 전술 변화 분석
├─ Historical Context (지난 3시즌)
└─ Multivariate 상황 분석
```

### 3️⃣ 본석 레포트
```
단순 예측: "LAL 42%"

우리의 리포트:
├─ Event Analysis
│  └─ LeBron 부상의 정확한 영향도
├─ Quantitative Proof
│  └─ 3시즌 데이터로 검증
├─ Market Gap Analysis
│  └─ 배당과의 불일치 분석 (당신 추가)
└─ Actionable Insights
   └─ 베팅 전략, 타이밍, 위험도
```

---

## 📋 현재 상태 체크리스트

### ✅ 완료된 것 (로컬)
```
✅ Player 데이터 (25속성, 653명)
✅ Coach 데이터 (12속성, 24명)
✅ Referee 데이터 (3속성 + Stats, 85명)
✅ GameState (2,249경기)
✅ PlayerBoxScore (14,140개)
✅ PlayerRecentForm (1,374개) - 자동 생성
✅ RefereeStats (79명) - 자동 생성
✅ TeamStrength (30개팀) - 자동 계산
✅ CoachStats (~60명) - 자동 계산
✅ RosterStats (30개팀) - 자동 계산
✅ daily_automation.py (매일 09:00 UTC)
```

### ⏳ 준비된 것 (VPS 설계)
```
✅ NBAEvent 수집 로직 (n8n g9_final_v8.json)
├─ Injury Event
├─ Lineup Change
├─ Referee Assignment
└─ Trade Event

✅ EconomicEvent 수집 로직
├─ Market Events
├─ Policy Changes
└─ Macro Indicators

✅ 워크플로우 3개
├─ g9_final_v8.json (기본)
├─ g9_ready_to_deploy.json (실제 배포)
└─ g9_production_final.json (RSS 안정형)
```

### 🔧 구현 필요 (이제 할 것)
```
🔨 Neo4j 스키마 확정
├─ NBAEvent 노드 정의
├─ EconomicEvent 노드 정의
├─ 관계 정의 (INJURY, INFLUENCES 등)
└─ 인덱스 설정

🔨 분석 엔진 개발
├─ Event 감지 시 Graph 재계산
├─ 영향도 분석 (Player/Team/Game)
├─ Confidence 계산
└─ Related 노드 찾기

🔨 리포트 생성 로직
├─ Situation Analysis
├─ Quantitative Insight
├─ Market Gap (당신이 배당 추가)
└─ Actionable Strategy

🔨 API/Dashboard
├─ Real-time Alert
├─ Report API
└─ Web Dashboard
```

### 🎁 당신이 추가할 것
```
💎 배당 데이터
├─ OddsEvent 수집
├─ Odds Movement 분석
├─ Market Sentiment
└─ Betting Pool Intelligence

💎 배당 분석 로직
├─ Odds vs Our Model 비교
├─ Discrepancy 감지
├─ Value Finding
└─ Betting Strategy
```

---

## 🚀 다음 단계

### 1. Neo4j 스키마 정확히 정의
```python
# NBAEvent
{
  event_id, type, player, team, status, reason,
  confidence, created_at, updated_at, source
}

# 관계
Player -[INJURY]-> InjuryEvent
Team -[LINEUP_CHANGE]-> LineupEvent
Game -[UPDATED_REFEREE]-> Referee
Player -[TRADED]-> Team
```

### 2. 분석 엔진 첫 번째 버전
```python
# 입력: NBAEvent
# 프로세스:
# 1. 영향받는 모든 노드 찾기
# 2. 각 노드의 통계 업데이트
# 3. Cascade 영향도 계산
# 4. 신뢰도 점수 계산
# 출력: AnalysisResult
```

### 3. 리포트 생성기
```python
# 입력: AnalysisResult
# 프로세스:
# 1. Situation 정리
# 2. Quantitative 근거 수집
# 3. 마켓 갭 분석
# 4. 전략 제시
# 출력: HTML/JSON Report
```

---

## 🎯 최종 그림

```
당신의 시스템이 제공하는 것:

1️⃣ Real-time Intelligence
   "LeBron OUT" → 1분 내 우리 분석 완료

2️⃣ Deep Analysis
   "단순 강도 감소" → "15.3pts, AD +2.1reb, 전술 변화"

3️⃣ Quantitative Report
   "예측 42%" → "데이터, 신뢰도, 근거, 전략"

4️⃣ Market Intelligence (당신이 추가)
   "배당 vs 우리 분석" → "10% 불일치 = Edge"

5️⃣ Actionable Strategy
   "GSW +3.0 베팅, 타이밍은 다음 30분 추적"

← 이게 배팅 시장에서 이길 수 있는 조합!
```

---

**다음으로 뭘 시작할까요?**
1. Neo4j 스키마 확정?
2. 분석 엔진 첫 버전?
3. VPS 배포 준비?
