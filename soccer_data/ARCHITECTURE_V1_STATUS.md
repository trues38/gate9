# Soccer Data Architecture v1.0 - Implementation Status

## Schema Definition Complete

### SQLite (정량 데이터)
**File**: `schema/soccer_sqlite_schema.sql`

| Table | Purpose | Status |
|-------|---------|--------|
| teams | 팀 기본 정보 | Loaded (110) |
| managers | 감독 정보 | Loaded (8) |
| referees | 심판 정보 | Loaded (32) |
| players | 선수 정보 | Ready |
| matches | 경기 결과 | Loaded (3,504) |
| match_stats | xG, 슛, 점유율 등 | Loaded (7,008) |
| odds_closing | 마감 배당 | Loaded (3,504) |
| odds_history | 라인 변동 | Ready |
| player_match_stats | 선수별 경기 스탯 | Ready |
| injuries | 부상 정보 | Ready |
| referee_stats | 심판 시즌 통계 | Ready |

**Database**: `data/soccer.db` (3.4 MB)

### Neo4j (관계/패턴 데이터)
**File**: `schema/soccer_neo4j_schema.cypher`

| Node Type | Purpose | Status |
|-----------|---------|--------|
| Team | 팀 + 리그 관계 | Ready |
| Manager | 감독 + 전술 선호 | Ready |
| Referee | 심판 + 편향 맥락 | Ready |
| Tactic | 전술 스타일 (14종) | Ready |
| Formation | 포메이션 (10종) | Ready |
| Pattern | 베팅 패턴 (8종) | Ready |
| Context | 심판 편향 맥락 (7종) | Ready |
| League | 5대 리그 | Ready |
| Match | 경기 노드 (thin) | Ready |

## v1.0 Key Features Implemented

### 1. Match Node (Thin)
```cypher
(Match) - id, date, league, home_team, away_team, referee
(Team)-[:PLAYED_IN {home/away}]->(Match)
(Referee)-[:OFFICIATED]->(Match)
```

### 2. Tactic with Time/Intensity
```cypher
(Team)-[:APPLIES {confidence, since, until, intensity}]->(Tactic)
```

### 3. Referee Bias by Context
```cypher
(Referee)-[:FAVORS {bias_score, sample_size, confidence}]->(Context)
Context types: home_team, away_team, big_team, small_team, derby
```

### 4. Common ID System
Shared between SQLite and Neo4j:
- `team_id`: normalized team name (e.g., "arsenal", "man_city")
- `manager_id`: normalized manager name (e.g., "pep_guardiola")
- `referee_id`: normalized referee name (e.g., "michael_oliver")
- `match_id`: format `{LEAGUE}_{home}_{away}_{YYYYMMDD}`

## Data Sources Loaded

| Source | Records | Coverage |
|--------|---------|----------|
| Historical Odds (football-data.co.uk) | 3,504 matches | 5 leagues x 2 seasons |
| Understat xG | 3,504 matches | xG/xGA merged |
| Manager Database | 8 managers | EPL top teams |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ingest_to_sqlite.py` | SQLite data loading |
| `scripts/ingest_to_neo4j.py` | Neo4j graph loading |

## Next Steps

1. **VPS Deployment**: Copy sqlite and scripts to VPS
2. **Neo4j Loading**: Run `ingest_to_neo4j.py` with VPS Neo4j
3. **Data Collection Pipeline**: Set up cron for daily updates
4. **LLM Integration**: Build query layer combining SQLite + Neo4j

## Usage Example

```python
# SQLite: Get match quantitative data
import sqlite3
conn = sqlite3.connect('data/soccer.db')
cursor = conn.execute('''
    SELECT m.*, ms.xg, ms.possession, oc.home_win
    FROM matches m
    JOIN match_stats ms ON m.match_id = ms.match_id
    JOIN odds_closing oc ON m.match_id = oc.match_id
    WHERE m.league = 'EPL' AND m.date > '2024-12-01'
''')

# Neo4j: Get team tactical context
session.run('''
    MATCH (t:Team {team_id: 'arsenal'})-[a:APPLIES]->(tac:Tactic)
    MATCH (t)<-[:MANAGES]-(m:Manager)-[:PREFERS]->(pref:Tactic)
    RETURN t.name, tac.name, a.confidence, m.name, pref.name
''')
```
