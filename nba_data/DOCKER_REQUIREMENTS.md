# VPS Docker에 가져갈 것

## 필요한 파일들

```
nba_data/state_graph/
├── daily_automation.py         (로컬: 매일 09:00 UTC)
├── generate_player_recent_form.py
├── generate_referee_stats.py
├── calculate_team_strength.py
├── calculate_coach_stats.py
├── create_player_team_relations.py
├── crawl_current_season_boxscores.py
└── boxscore_api.py
```

## Flask API 구조 (Docker에서 새로 만들 것)

```
flask-api/
├── app.py
│   ├── POST /nba/analyze      (NBAEvent → Graph 계산)
│   ├── POST /economy/regime   (Economy → 분석)
│   └── POST /report           (Report 생성)
├── requirements.txt
│   └─ neo4j, flask, python-dotenv
└── Dockerfile
```

## Docker Compose (3개 서비스)

```
services:
  neo4j       (데이터베이스)
  n8n         (실시간 수집)
  flask       (분석 엔진)
```

## Neo4j에 들어갈 데이터

```
daily_automation.py가 매일 만드는 것:
├─ Player (25속성)
├─ Coach (12속성)
├─ Referee + RefereeStats
├─ GameState + PlayerBoxScore
├─ PlayerRecentForm
├─ TeamStrength
├─ CoachStats
├─ RosterStats
└─ PLAYS_FOR 관계
```

## 정리

```
✅ nba_data/state_graph/ → 도커로 가져갈 준비됨
✅ Flask API 로직 → Docker 안에서 새로 만들 것
✅ 문서 (CORE_SYSTEM_ARCHITECTURE.md) → 도커에 복사
```
