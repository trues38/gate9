# Neo4j 스키마 정의 필요

## 현재 상태
```
✅ 기존 노드들 (이미 있음):
├─ Player, Team, Coach, Referee
├─ GameState, PlayerBoxScore
└─ PlayerRecentForm, RefereeStats, TeamStrength, CoachStats, RosterStats

❌ VPS에서 새로 필요한 노드들 (정의 안 됨):
├─ NBAEvent
├─ EconomicEvent
├─ InjuryEvent
├─ LineupEvent
├─ TradeEvent
└─ OddsSnapshot (당신이 추가할 부분)
```

## 내가 준비하지 않은 것들

### 1️⃣ NBAEvent 노드 스키마
```
NBAEvent {
  event_id: string (UNIQUE)
  type: enum (injury | lineup | referee | trade)
  player: string
  team: string
  status: string
  reason: string
  confidence: float
  created_at: datetime
  updated_at: datetime
  source: string
}
```

### 2️⃣ 관계 정의
```
Player -[INJURY]-> InjuryEvent
Team -[LINEUP_CHANGE]-> LineupEvent
Referee -[UPDATED_ASSIGNMENT]-> Game
Player -[TRADED]-> Team
```

### 3️⃣ 인덱스/제약조건
```
UNIQUE: NBAEvent.event_id
INDEX: NBAEvent.created_at
INDEX: NBAEvent.type
CONSTRAINT: Player.name UNIQUE
```

### 4️⃣ 마이그레이션 스크립트
```
neo4j_schema_setup.py
└─ NBAEvent 노드 생성
└─ 관계 정의
└─ 인덱스 생성
```

## 내가 정의할 것

```
✅ 새로 만들 파일:
├─ nba_data/neo4j_schema.py
│  └─ NBAEvent, EconomicEvent 노드 정의
├─ nba_data/neo4j_constraints.py
│  └─ 모든 제약조건 및 인덱스
└─ nba_data/neo4j_setup.py
   └─ Docker에서 실행할 초기화 스크립트
```

## 당신이 하는 부분

```
❌ 배당 관련 노드:
├─ OddsSnapshot
├─ OddsMovement
└─ 관계들
```
