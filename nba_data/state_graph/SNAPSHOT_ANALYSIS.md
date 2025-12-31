# NBA 데이터 스냅샷 분석 및 생성 계획

**분석일**: 2025-12-26

---

## ✅ 현재 있는 데이터

### 1. Player 노드 (653명)
**시즌 평균 통계** - ✅ 완료
```
- ppg, rpg, apg (시즌 평균)
- fg_pct, three_pct, ft_pct
- avg_minutes, avg_plus_minus
- impact_percentile, injury_prone, stamina
- style_tags (oreb-specialist, playmaker 등)
```

### 2. Coach 노드 (24팀)
**로테이션 통계** - ✅ 완료
```
- rotation_depth (로테이션 깊이)
- avg_starter_minutes, avg_bench_minutes
- tempo (경기 템포)
- win_pct (승률)
- rookie_trust, veteran_bias
```

### 3. PlayerBoxScore (14,140개)
**경기별 상세 기록** - ✅ 완료
```
- 경기별 points, rebounds, assists
- FG%, 3PT%, FT%
- plus_minus
- 날짜별 추적 가능
```

### 4. Referee (85명)
**기본 정보만** - ⚠️ 통계 없음
```
- name (이름만)
→ 심판별 통계 필요
```

### 5. Team (36팀)
**기본 정보만** - ⚠️ 통계 없음
```
- name, abbr (이름만)
→ 팀별 통계 필요
```

### 6. Reddit 데이터 (188개)
**여론 분석** - ✅ 완료
```
- RedditPost (43개)
- RedditComment (134개)
- SentimentSummary (7개 선수)
- TeamSentiment (4개 팀)
```

---

## ❌ 없는 데이터 (필요한 스냅샷)

### 🔥 1순위: 선수별 최근 폼 (베팅 핵심)

**PlayerRecentForm** 노드 생성
```cypher
(:Player)-[:HAS_RECENT_FORM]->(:PlayerRecentForm {
  period: 'L5' | 'L10' | 'L15',
  ppg: FLOAT,
  rpg: FLOAT,
  apg: FLOAT,
  fg_pct: FLOAT,
  plus_minus: FLOAT,
  games_played: INT,
  trend: 'hot' | 'cold' | 'stable',
  updated_at: DATETIME
})
```

**중요도**: ⭐⭐⭐⭐⭐
**이유**: "Curry 최근 5경기 평균 35점" 같은 질문에 즉답
**베팅 영향**: 최근 폼이 좋으면 Over 베팅 유리

---

### 🔥 2순위: 심판별 통계 (차별화 포인트)

**RefereeStats** 노드 생성
```cypher
(:Referee)-[:HAS_STATS]->(:RefereeStats {
  season: '2025-26',
  total_games: INT,
  avg_total_fouls: FLOAT,
  avg_home_fouls: FLOAT,
  avg_away_fouls: FLOAT,
  home_team_win_pct: FLOAT,
  avg_game_total_points: FLOAT,
  over_under_bias: 'over' | 'under' | 'neutral',
  updated_at: DATETIME
})
```

**중요도**: ⭐⭐⭐⭐⭐
**이유**: "Tony Brothers 심판이면 어느 팀 유리?" - 경쟁사 없음
**베팅 영향**: 심판에 따라 Over/Under, 홈/원정 승률 달라짐

---

### 🔥 3순위: 팀별 최근 폼

**TeamRecentForm** 노드 생성
```cypher
(:Team)-[:HAS_RECENT_FORM]->(:TeamRecentForm {
  period: 'L5' | 'L10',
  wins: INT,
  losses: INT,
  win_pct: FLOAT,
  ppg: FLOAT,
  opp_ppg: FLOAT,
  avg_margin: FLOAT,
  trend: 'winning_streak' | 'losing_streak' | 'stable',
  updated_at: DATETIME
})
```

**중요도**: ⭐⭐⭐⭐
**이유**: "Warriors 최근 5경기 5승" - 팀 모멘텀
**베팅 영향**: 연승/연패 중인 팀의 배당률 변화

---

### 4순위: 선수별 홈/원정 스플릿

**PlayerSplit** 노드 생성
```cypher
(:Player)-[:HAS_SPLIT]->(:PlayerSplit {
  split_type: 'home' | 'away',
  season: '2025-26',
  ppg: FLOAT,
  rpg: FLOAT,
  apg: FLOAT,
  fg_pct: FLOAT,
  games: INT,
  diff_from_avg: FLOAT
})
```

**중요도**: ⭐⭐⭐
**이유**: "LeBron은 홈에서 더 잘하나?"
**베팅 영향**: 홈/원정 성적 차이 큰 선수 식별

---

### 5순위: 팀별 홈/원정 스플릿

**TeamSplit** 노드 생성
```cypher
(:Team)-[:HAS_SPLIT]->(:TeamSplit {
  split_type: 'home' | 'away',
  season: '2025-26',
  wins: INT,
  losses: INT,
  win_pct: FLOAT,
  ppg: FLOAT,
  opp_ppg: FLOAT
})
```

**중요도**: ⭐⭐⭐
**이유**: 팀마다 홈/원정 차이 큼
**베팅 영향**: 홈 강팀 vs 원정 약팀 파악

---

### 6순위: 백투백 성적

**PlayerBackToBack** / **TeamBackToBack**
```cypher
(:Player)-[:HAS_B2B_STATS]->(:BackToBackStats {
  games: INT,
  ppg: FLOAT,
  minutes: FLOAT,
  diff_from_avg: FLOAT
})
```

**중요도**: ⭐⭐⭐
**이유**: 백투백 경기는 피로도 ↑
**베팅 영향**: 주전 선수 출전 시간 감소, Under 유리

---

### 7순위: 팀 vs 팀 매치업 히스토리

**TeamMatchup** 노드 생성
```cypher
(:Team)-[:MATCHUP_HISTORY {
  opponent: STRING,
  season: '2025-26',
  wins: INT,
  losses: INT,
  avg_margin: FLOAT,
  last_meeting_date: DATE,
  last_meeting_result: 'W' | 'L'
}]->(:Team)
```

**중요도**: ⭐⭐
**이유**: "Lakers vs Warriors 올시즌 전적은?"
**베팅 영향**: 상성 파악 (특정 팀에 약한 팀)

---

### 8순위: 선수 vs 심판 조합

**PlayerRefereeStats**
```cypher
(:Player)-[:WITH_REFEREE]->(:PlayerRefereeStats {
  referee: STRING,
  games: INT,
  ppg: FLOAT,
  fouls_pg: FLOAT,
  tech_fouls: INT,
  diff_from_avg: FLOAT
})
```

**중요도**: ⭐⭐
**이유**: "Trae Young + Tony Brothers 조합"
**베팅 영향**: 특정 심판과 궁합 나쁜 선수 (파울 트러블)

---

## 🎯 생성 우선순위 (베팅 관점)

### Phase 1: 즉시 생성 (핵심)
1. ✅ **PlayerRecentForm (L5, L10)**
2. ✅ **RefereeStats**
3. ✅ **TeamRecentForm (L5, L10)**

**예상 시간**: 1-2시간
**효과**: 베팅 질문 80% 커버

---

### Phase 2: 중요 (1주 내)
4. **PlayerSplit (홈/원정)**
5. **TeamSplit (홈/원정)**
6. **BackToBackStats**

**예상 시간**: 2-3시간
**효과**: 베팅 질문 95% 커버

---

### Phase 3: 추가 (나중에)
7. **TeamMatchup**
8. **PlayerRefereeStats**

**예상 시간**: 2시간
**효과**: 100% 완벽

---

## 📊 데이터 생성 방법

### 1. PlayerRecentForm 생성
```python
# 스크립트: calculate_player_recent_form.py

for player in players:
    for period in ['L5', 'L10', 'L15']:
        # PlayerBoxScore에서 최근 N경기 조회
        recent_games = get_recent_games(player, n=period)

        # 평균 계산
        form = {
            'ppg': avg(recent_games.points),
            'rpg': avg(recent_games.rebounds),
            'apg': avg(recent_games.assists),
            'trend': calculate_trend(recent_games)
        }

        # Neo4j 저장
        create_player_recent_form(player, period, form)
```

### 2. RefereeStats 생성
```python
# 스크립트: calculate_referee_stats.py

for referee in referees:
    # 해당 심판이 심판본 모든 경기 조회
    games = get_games_by_referee(referee)

    stats = {
        'total_games': len(games),
        'avg_total_fouls': avg([g.fouls for g in games]),
        'home_team_win_pct': calculate_home_win_pct(games),
        'avg_game_total_points': avg([g.total_points for g in games]),
        'over_under_bias': determine_bias(games)
    }

    create_referee_stats(referee, stats)
```

### 3. TeamRecentForm 생성
```python
# 스크립트: calculate_team_recent_form.py

for team in teams:
    for period in ['L5', 'L10']:
        recent_games = get_recent_team_games(team, n=period)

        form = {
            'wins': count_wins(recent_games),
            'losses': count_losses(recent_games),
            'ppg': avg([g.team_points for g in recent_games]),
            'trend': 'winning_streak' if all_wins else 'stable'
        }

        create_team_recent_form(team, period, form)
```

---

## 🤔 생성해야 할까?

### 👍 생성하면 좋은 점
1. **그래프 RAG 정확도 ↑**: "Curry 최근 폼은?" 즉답 가능
2. **베팅 인사이트 제공**: 심판 변수, 홈/원정 차이
3. **차별화**: 경쟁사는 심판 통계 없음
4. **자동 업데이트**: 매일 Box Score 수집 후 재계산

### 👎 생성 안 해도 되는 경우
1. **계산 가능**: PlayerBoxScore에서 실시간 계산
2. **초기 MVP**: 기본 데이터만으로도 충분
3. **복잡도 증가**: 노드/관계 늘어남

---

## 💡 추천

**Phase 1만 우선 생성** (1-2시간):
- PlayerRecentForm (L5, L10)
- RefereeStats
- TeamRecentForm (L5, L10)

**이유**:
- 베팅 질문 80% 커버
- 차별화 포인트 확보 (심판)
- 나머지는 필요 시 생성

---

## 🚀 다음 단계

1. **생성 스크립트 작성** (30분)
2. **Neo4j 스키마 정의** (10분)
3. **초기 데이터 생성** (30분)
4. **자동 업데이트 설정** (Flask API에 통합, 20분)

**총 소요 시간**: 1.5시간

---

**작성일**: 2025-12-26
**결론**: Phase 1 (최근 폼 + 심판 통계) 생성 추천
