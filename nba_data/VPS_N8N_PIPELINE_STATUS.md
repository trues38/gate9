# VPS n8n 파이프라인 구조 분석

## 📋 현황

**메인 VPS 파이프라인**: `/Users/js/g9/n8n_workflows/`에 3개 워크플로우

```
1️⃣ g9_final_v8.json (핵심 설계)
   ├─ NBA 실시간 모니터링 (5PM-11PM ET)
   └─ Economy 일일 분석 (9AM UTC)

2️⃣ g9_ready_to_deploy.json (개선 버전)
   ├─ NBA Twitter API 통합
   └─ Economy와 Link 관계까지

3️⃣ g9_production_final.json (RSS 기반)
   ├─ NBA RSS 피드 통합 (Shams, Woj, NBA Refs)
   └─ Gemini 분석 추가
```

---

## 🏗️ VPS 파이프라인 아키텍처

### 1️⃣ **g9_final_v8.json** (기본 설계)

#### NBA 부분 (실시간)
```
5PM-11PM ET Cron
├─ Check NBA Schedule
│  └─ (경기 없으면 스킵)
├─ Fetch NBA Whitelist
│  └─ (정규식 기반 키워드 필터링)
├─ Parse NBA Event (Logic)
│  └─ (LLM 미사용, 정규식으로 비용 $0)
│     ├─ event_type: injury / referee / lineup / trade
│     ├─ player name
│     ├─ team
│     ├─ status: OUT / GTD / QUESTIONABLE
│     └─ reason: ankle / knee / illness 등
└─ Store NBA Event → Neo4j
   └─ NBAEvent 노드 생성
```

**수집 이벤트:**
- 부상/결장 (Injury)
- 라인업 (Lineup)
- 심판 (Referee)
- 거래 (Trade)

**비용:** $0 (정규식 기반)

#### Economy 부분 (일일)
```
9AM UTC Trigger
├─ Economy X Search (Grok)
│  └─ OpenRouter API 호출
├─ Parse Search Results
│  └─ 신뢰도 필터링
├─ Economy Analysis (Grok Fast)
│  └─ 이벤트 분류
└─ Parse Economy Events
   └─ Neo4j 저장 준비
```

**이벤트 도메인:**
- 금리 변화 (Interest Rate)
- 인플레이션 (Inflation)
- 실업률 (Unemployment)
- GDP 성장 (GDP Growth)
- 기업 실적 (Earnings)

**비용:** OpenRouter API (Grok) 사용

---

### 2️⃣ **g9_ready_to_deploy.json** (실제 배포용)

**개선사항:**
```
NBA:
├─ HTTP 기반 NBA Schedule API 호출
├─ Twitter API 직접 통합
├─ 더 정교한 키워드 필터링
└─ Link 관계 생성

Economy:
├─ X Search와 Grok 분석 통합
├─ Store Economy Event
└─ InfluenceFactors 관계 링크
```

**추가 기능:**
- Store → Link: Economy Event를 InfluenceFactors와 연결
- 팀/선수에 대한 영향도 추적

---

### 3️⃣ **g9_production_final.json** (RSS 기반)

**특징:**
```
NBA RSS 피드:
├─ Shams Charania RSS
├─ Woj ESPN RSS
└─ NBA Refs RSS

처리:
├─ Merge: 3개 RSS 통합
├─ Filter: 키워드 필터링
├─ Extract: Grok-2 모델로 구조화
└─ Store: Neo4j 저장

Economy:
├─ Grok X Search (고급)
├─ Gemini 분석 (더 정확)
├─ Store Economy Event
└─ Link to InfluenceFactors
```

**장점:** RSS는 안정적, 비용 효율적

---

## 🔄 데이터 흐름

### NBA 실시간 데이터 수집

```
Twitter/Whitelist (실시간)
├─ Shams Charania
├─ Woj ESPN
├─ NBA Official Refs
└─ News Sources

→ 정규식/Logic 파싱

→ NBAEvent 노드 생성
├─ event_type: injury / referee / trade
├─ player: string
├─ team: string
├─ status: string
├─ reason: string
└─ confidence: float

→ Neo4j 저장
└─ Player/Team과 관계 연결
```

### Economy 일일 데이터 수집

```
9AM UTC Trigger

→ X Search (Grok 쿼리)
   ├─ economic indicators
   ├─ market news
   └─ policy changes

→ Grok 분석/분류

→ EconomicEvent 노드 생성
├─ domain: rates / inflation / gdp / employment
├─ event_type: positive / negative / neutral
├─ impact_score: float
└─ affected_sectors: list

→ Neo4j 저장
└─ InfluenceFactors와 관계 연결
   ├─ Player → affected
   ├─ Team → affected
   └─ Game → influenced
```

---

## 📊 VPS가 채울 것 (현재 미지원)

### ✅ 이미 설계됨

```
VPS n8n이 수집할 데이터:

1. NBA Event
   ├─ Injury (부상/결장)
   │  └─ Player -[INJURY]-> InjuryEvent
   ├─ Lineup (라인업 변경)
   │  └─ Team -[LINEUP_CHANGE]-> LineupEvent
   ├─ Referee (심판 배정)
   │  └─ Game -[OFFICIATED_BY_UPDATED]-> Referee
   └─ Trade (트레이드)
      ├─ Player -[TRADED]-> Team
      └─ Team -[ACQUIRED]-> Player

2. Economy Event
   ├─ Market Events
   ├─ Policy Changes
   └─ Macro Indicators

3. InfluenceFactors
   └─ Sports와 Economy의 교집합
```

### ❌ 아직 Neo4j 노드 정의 필요

```
NBAEvent {
  event_id: string
  type: enum (injury|lineup|referee|trade)
  player: string
  team: string
  status: string
  reason: string
  confidence: float
  created_at: datetime
}

EconomicEvent {
  event_id: string
  domain: string
  type: string
  impact_score: float
  sectors_affected: list
  created_at: datetime
}

InfluenceFactors {
  factor_id: string
  nba_event: string
  economic_event: string
  correlation_score: float
  description: string
}
```

---

## 🚀 다음 단계

### 1. VPS에서 실행할 n8n 워크플로우 선택

```
옵션 A: g9_final_v8.json (최소 비용)
└─ 정규식 + Grok만 사용
└─ 비용: OpenRouter API 요금만

옵션 B: g9_ready_to_deploy.json (균형)
└─ Twitter API + Grok + Link
└─ 비용: 중간 수준

옵션 C: g9_production_final.json (안정성)
└─ RSS + Grok + Gemini + Link
└─ 비용: 높지만 안정적
```

### 2. Neo4j 스키마 정의

```
NBAEvent 노드 생성 규칙:
├─ -[HAS_INJURY]-> InjuryEvent → Player
├─ -[LINEUP_CHANGE]-> LineupEvent → Team
├─ -[UPDATED_REFEREE]-> Referee
└─ -[TRADE]-> TradeEvent → (Player, Team)

EconomicEvent와 연결:
├─ -[INFLUENCES]-> Player
├─ -[INFLUENCES]-> Team
└─ -[INFLUENCES]-> Game
```

### 3. 자동화 스케줄

```
NBA (실시간):
├─ 5PM-11PM ET: 매시간 정각
└─ 경기 중심 (경기 있는 날만)

Economy (일일):
├─ 9AM UTC (2PM KST): 매일 한 번
└─ 시장 지표 수집
```

---

## 📝 현재 로컬 자동화와의 관계

| 작업 | 로컬 (daily_automation.py) | VPS (n8n) |
|------|---------------------------|----------|
| BoxScore 수집 | ✅ NBA API | - |
| PlayerRecentForm | ✅ 로컬 계산 | - |
| RefereeStats | ✅ 로컬 계산 | - |
| TeamStrength | ✅ 로컬 계산 | - |
| CoachStats | ✅ 로컬 계산 | - |
| | | |
| **NBA Event** | - | ✅ 실시간 (VPS) |
| **Injury 추적** | - | ✅ 실시간 (VPS) |
| **Trade 추적** | - | ✅ 실시간 (VPS) |
| **Economy 수집** | - | ✅ 일일 (VPS) |
| **InfluenceFactors** | - | ✅ 계산 (VPS) |

---

## 🎯 결론

**로컬 (매일 09:00 UTC):**
- 경기 결과 수집
- 선수 통계 계산
- 팀 강도 재계산

**VPS (실시간 + 일일):**
- 부상/라인업 변수 추적
- 트레이드 기록
- 경제 지표 수집
- 영향도 분석

**이 조합이면:**
- ✅ 선수/팀/심판/감독: 완벽
- ✅ 경기 결과: 완벽
- ✅ 동적 변수 (부상/트레이드): VPS 필요
- ✅ 경제 영향도: VPS 필요

---

**최종 상태:** VPS 파이프라인 설계 완료 ✅
**다음:** VPS 서버에 n8n 배포 및 워크플로우 실행
