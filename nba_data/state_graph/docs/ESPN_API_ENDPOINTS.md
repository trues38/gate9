# ESPN NBA API Endpoints (Phase 1)

## Primary Data Sources

### 1. Scoreboard API (경기 일정)
```
GET http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={YYYYMMDD}
```

**Response Structure:**
```json
{
  "leagues": [...],
  "events": [
    {
      "id": "401736815",
      "date": "2024-12-16T...",
      "name": "Charlotte Hornets at Philadelphia 76ers",
      "shortName": "CHA @ PHI",
      "competitions": [
        {
          "id": "...",
          "venue": {...},
          "competitors": [
            {"homeAway": "home", "team": {"abbreviation": "PHI"}},
            {"homeAway": "away", "team": {"abbreviation": "CHA"}}
          ],
          "status": {"type": {"state": "post"}}
        }
      ]
    }
  ]
}
```

**Key Fields:**
- `events[].id` → game_id (Summary API 호출용)
- `events[].competitions[].competitors[]` → 팀 정보
- `events[].status.type.state` → "pre", "in", "post"

---

### 2. Summary API (경기 상세)
```
GET http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}
```

**Response Structure:**
```json
{
  "boxscore": { "teams": [...], "players": [...] },
  "gameInfo": {
    "venue": {...},
    "attendance": 20000,
    "officials": [
      {"fullName": "Sean Wright", "position": {"name": "Referee"}}
    ]
  },
  "injuries": [
    {
      "team": {"displayName": "Charlotte Hornets"},
      "injuries": [
        {
          "athlete": {"displayName": "Grant Williams"},
          "status": "Out",
          "type": {"description": "out"}
        }
      ]
    }
  ],
  "standings": [...],
  "header": {...}
}
```

**Key Fields:**
- `gameInfo.officials[]` → 심판 정보
- `injuries[]` → 팀별 부상자 목록
- `boxscore.teams[]` → 팀 스탯
- `standings[]` → 시즌 순위/기록

---

### 3. Team Roster API (팀 로스터)
```
GET http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster
```

**Response Structure:**
```json
{
  "team": {
    "id": "13",
    "displayName": "Los Angeles Lakers",
    "abbreviation": "LAL"
  },
  "athletes": [
    {
      "id": "...",
      "displayName": "LeBron James",
      "jersey": "23",
      "position": {"abbreviation": "F"},
      "injuries": [
        {"status": "Day-To-Day", "type": "..."}
      ]
    }
  ],
  "coach": [...]
}
```

**Key Fields:**
- `athletes[]` → 선수 목록
- `athletes[].injuries[]` → 개별 선수 부상 상태

---

## ESPN Team ID Mapping

| Team | ID | | Team | ID |
|------|----|-|------|-----|
| ATL | 1 | | MEM | 29 |
| BOS | 2 | | MIA | 14 |
| BKN | 17 | | MIL | 15 |
| CHA | 30 | | MIN | 16 |
| CHI | 4 | | NOP | 3 |
| CLE | 5 | | NYK | 18 |
| DAL | 6 | | OKC | 25 |
| DEN | 7 | | ORL | 19 |
| DET | 8 | | PHI | 20 |
| GSW | 9 | | PHX | 21 |
| HOU | 10 | | POR | 22 |
| IND | 11 | | SAC | 23 |
| LAC | 12 | | SAS | 24 |
| LAL | 13 | | TOR | 28 |
| UTA | 26 | | WAS | 27 |

---

## Data Flow

```
[Scoreboard API] → 날짜별 경기 목록 (game_id 획득)
        ↓
[Summary API] → 경기별 상세 (심판, 부상, 스탯)
        ↓
[Roster API] → 팀별 선수 상태 (보완용)
        ↓
[State Snapshot] → 통합 상태 JSON
```

---

## Rate Limiting

- 권장 딜레이: 200ms per request
- ESPN API는 공개 API지만 과도한 요청 시 차단 가능
