# 진짜 Graph RAG 구현 전략

## 문제 정의

**잘못된 접근:**
```python
# ❌ 모든 데이터를 LLM에게 주기
all_nodes = neo4j.query("MATCH (n) RETURN n")  # 15,433 nodes
context = str(all_nodes)  # 폭발!
llm(context)  # 토큰 한도 초과
```

**올바른 접근:**
```python
# ✅ 필요한 쿼리만 선택적 실행
queries = select_relevant_queries(matchup)  # 5-10개 쿼리
context = execute_queries(queries)  # 관련 데이터만
llm(context)  # 풍부하지만 집중된 컨텍스트
```

---

## 전략 1: "Core Query Set" (기본 세트)

**모든 경기마다 항상 실행할 10개 쿼리**

### 1. H2H History (상세)
```cypher
MATCH (g:Game)
WHERE g.home_team = $team_a AND g.away_team = $team_b
   OR g.home_team = $team_b AND g.away_team = $team_a
RETURN g.date, g.home_team, g.away_team, g.home_score, g.away_score,
       g.home_team + ' ' + g.home_score + '-' + g.away_score + ' ' + g.away_team as summary
ORDER BY g.date DESC
LIMIT 5
```

**출력 예:**
```
20241120: PHI 111 @ MEM 117 (MEM 홈승, 6점차)
20241102: MEM 124 @ PHI 107 (MEM 원정승, 17점차 블로우아웃!)
```

### 2. 최근 5경기 (상대팀 강도 포함)
```cypher
MATCH (g:Game)-[:PLAYED_BY]->(t:Team {abbr: $team})
MATCH (opponent:Team)
WHERE (g.home_team = opponent.abbr OR g.away_team = opponent.abbr)
  AND opponent.abbr != $team
RETURN g.date,
       opponent.name,
       opponent.win_pct as opponent_strength,  // 핵심!
       g.score,
       CASE WHEN g.winner = $team THEN 'W' ELSE 'L' END as result
ORDER BY g.date DESC
LIMIT 5
```

**출력 예:**
```
vs OKC (승률 75%) - L 129-104  → 강팀에게 대패
vs CHI (승률 35%) - L 109-102  → 약팀에게 고전!
```

### 3. 홈/원정 분리 통계
```cypher
MATCH (g:Game)
WHERE g.home_team = $team
WITH AVG(g.home_score) as home_avg_scored,
     AVG(g.away_score) as home_avg_allowed,
     COUNT(*) as home_games

MATCH (g2:Game)
WHERE g2.away_team = $team
WITH home_avg_scored, home_avg_allowed, home_games,
     AVG(g2.away_score) as away_avg_scored,
     AVG(g2.home_score) as away_avg_allowed,
     COUNT(*) as away_games

RETURN home_avg_scored, home_avg_allowed, home_games,
       away_avg_scored, away_avg_allowed, away_games
```

### 4. 백투백 여부 & 피로도
```cypher
MATCH (g:Game {date: $game_date})
WHERE g.home_team = $team OR g.away_team = $team

MATCH (prev:Game)
WHERE (prev.home_team = $team OR prev.away_team = $team)
  AND prev.date < $game_date

WITH g, prev,
     duration.between(date(prev.date), date(g.date)).days as days_rest
ORDER BY prev.date DESC
LIMIT 1

RETURN days_rest,
       CASE
         WHEN days_rest = 0 THEN 'BACK_TO_BACK'
         WHEN days_rest = 1 THEN 'ONE_DAY_REST'
         ELSE 'WELL_RESTED'
       END as fatigue_level
```

### 5. 페이스 트렌드 (최근 5경기)
```cypher
MATCH (g:Game)
WHERE g.home_team = $team OR g.away_team = $team
WITH g, (g.home_score + g.away_score) as total_points
ORDER BY g.date DESC
LIMIT 5
RETURN AVG(total_points) as avg_total,
       COUNT(CASE WHEN total_points > 220 THEN 1 END) as high_pace_games,
       COUNT(CASE WHEN total_points < 200 THEN 1 END) as low_pace_games
```

### 6. 수비 vs 상대 공격력 매치업
```cypher
// 우리 팀 수비 vs 상대 공격력
MATCH (us:Team {abbr: $our_team})
MATCH (them:Team {abbr: $opponent})
RETURN us.avg_points_allowed as our_defense,
       them.avg_points_scored as their_offense,
       (them.avg_points_scored - us.avg_points_allowed) as mismatch
```

### 7. 클러치 타임 기록 (4쿼터 득점력)
```cypher
MATCH (g:Game)-[:HAS_QUARTER]->(q:Quarter {number: 4})
WHERE g.home_team = $team OR g.away_team = $team
WITH g, q,
     CASE WHEN g.home_team = $team THEN q.home_points ELSE q.away_points END as our_4q_points
ORDER BY g.date DESC
LIMIT 10
RETURN AVG(our_4q_points) as avg_4th_quarter_points,
       MAX(our_4q_points) as best_4q,
       MIN(our_4q_points) as worst_4q
```

### 8. 최근 승리/패배의 점수차 분포
```cypher
MATCH (g:Game)
WHERE (g.home_team = $team OR g.away_team = $team)
  AND g.date >= date() - duration({days: 30})

WITH g,
     ABS(g.home_score - g.away_score) as point_diff,
     CASE WHEN g.winner = $team THEN 'W' ELSE 'L' END as result

RETURN result,
       AVG(point_diff) as avg_margin,
       MAX(point_diff) as max_margin,
       COUNT(CASE WHEN point_diff > 15 THEN 1 END) as blowouts
```

### 9. 리바운드 지배력
```cypher
MATCH (g:Game)-[:STATS]->(s:TeamStats)
WHERE g.home_team = $team OR g.away_team = $team
RETURN AVG(s.offensive_rebounds) as avg_oreb,
       AVG(s.defensive_rebounds) as avg_dreb,
       AVG(s.total_rebounds) as avg_total_reb
```

### 10. 3점 슛 의존도 & 효율
```cypher
MATCH (g:Game)-[:STATS]->(s:TeamStats)
WHERE s.team = $team
RETURN AVG(s.three_point_attempts) as avg_3pa,
       AVG(s.three_point_made) as avg_3pm,
       AVG(s.three_point_percentage) as three_pct,
       (AVG(s.three_point_made * 3.0) / AVG(s.total_points)) * 100 as pct_from_three
```

---

## 전략 2: "Conditional Queries" (조건부)

**Core Query 결과를 보고 추가 쿼리 결정**

### 예시: H2H 5-0 지배를 발견했을 때

```python
h2h_result = core_query_1()  # H2H History

if is_dominant_h2h(h2h_result):  # 5-0, 4-1 등
    # 추가 쿼리: "왜 지배하는가?"

    # Query A: 각 H2H 경기의 쿼터별 득점
    quarter_breakdown = query("""
        MATCH (g:Game)-[:HAS_QUARTER]->(q:Quarter)
        WHERE g in $h2h_games
        RETURN g.date, q.number, q.home_points, q.away_points
    """)

    # Query B: H2H에서 특정 선수 지배력
    player_dominance = query("""
        MATCH (g:Game)-[:PLAYED_IN]->(p:Player)-[:ON_TEAM]->(t:Team)
        WHERE g in $h2h_games AND t.abbr = $dominant_team
        RETURN p.name, AVG(p.points) as avg_points, AVG(p.assists) as avg_assists
        ORDER BY avg_points DESC
        LIMIT 3
    """)
```

### 예시: 최근 폼에서 블로우아웃 패배 발견

```python
recent_games = core_query_2()

blowout_losses = [g for g in recent_games if g['margin'] > 20 and g['result'] == 'L']

if blowout_losses:
    # 추가 쿼리: "블로우아웃 패배의 공통점?"

    # Query C: 그 경기들의 턴오버 수
    turnover_analysis = query("""
        MATCH (g:Game {id: $game_id})-[:STATS]->(s:TeamStats)
        WHERE s.team = $team
        RETURN g.date, s.turnovers, s.opponent_fast_break_points
    """)

    # Query D: 상대팀의 공통점 (모두 상위권?)
    opponent_pattern = query("""
        MATCH (g:Game {id: $game_id})-[:OPPONENT]->(opp:Team)
        RETURN opp.name, opp.conference_rank, opp.defensive_rating
    """)
```

---

## 전략 3: "Pattern-Based Templates"

**자주 등장하는 분석 패턴별 쿼리 템플릿**

### Template A: "수비 붕괴 vs 엘리트 수비" 매치업

```python
if abs(team_a_def - team_b_def) > 10:  # 수비 효율 차이 10+

    defense_deep_dive = execute_queries([
        "paint_points_allowed",      # 페인트 실점
        "perimeter_defense_rating",  # 페리미터 수비
        "transition_defense",        # 전환 수비
        "defensive_rebound_pct"      # 수비 리바운드율
    ])
```

### Template B: "홈 코트 어드밴티지" 분석

```python
if location == 'home' and team_home_record > 0.65:

    home_court_analysis = execute_queries([
        "home_win_streak",          # 홈 연승
        "home_scoring_advantage",   # 홈 득점 차이
        "home_crowd_impact",        # 관중 영향 (FT%, 심판)
        "home_rest_advantage"       # 홈 휴식 이점
    ])
```

### Template C: "복수전" 시나리오

```python
if recent_h2h_loss and is_home_game:

    revenge_analysis = execute_queries([
        "last_h2h_game_breakdown",   # 최근 맞대결 상세
        "roster_changes_since",      # 이후 로스터 변화
        "momentum_shift",            # 모멘텀 변화
        "coach_adjustments"          # 코치 전술 변화
    ])
```

---

## 구현 예시: `SmartGraphRAG` 클래스

```python
class SmartGraphRAG:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.core_queries = self._load_core_queries()
        self.templates = self._load_templates()

    def analyze_matchup(self, team_a, team_b, game_date):
        """
        스마트하게 쿼리를 선택해서 실행
        """

        # Step 1: Core Queries (항상 실행)
        core_data = self._execute_core_queries(team_a, team_b)

        # Step 2: Pattern Detection
        patterns = self._detect_patterns(core_data)
        # 예: {"defensive_mismatch": True, "h2h_dominance": True, "revenge_game": False}

        # Step 3: Conditional Queries (패턴 기반)
        additional_data = {}

        if patterns['defensive_mismatch']:
            additional_data['defense'] = self._query_defensive_breakdown(team_a, team_b)

        if patterns['h2h_dominance']:
            additional_data['h2h_deep'] = self._query_h2h_details(team_a, team_b)

        # Step 4: Build Rich Context
        context = self._build_context(core_data, additional_data, patterns)

        return context

    def _detect_patterns(self, core_data):
        """
        Core Query 결과에서 패턴 감지
        """
        patterns = {}

        # 수비 미스매치
        def_diff = abs(core_data['team_a_def'] - core_data['team_b_def'])
        patterns['defensive_mismatch'] = def_diff > 10

        # H2H 지배
        h2h = core_data['h2h']
        h2h_record = sum(1 for g in h2h if g['winner'] == 'team_a')
        patterns['h2h_dominance'] = h2h_record >= 4  # 4승 이상

        # 블로우아웃 경향
        recent = core_data['recent_games']
        blowouts = sum(1 for g in recent if abs(g['margin']) > 15)
        patterns['blowout_tendency'] = blowouts >= 3

        return patterns
```

---

## 실제 적용 예시

### PHI @ MEM 경기

**Step 1: Core Queries 실행**
```
H2H: MEM 3-1
Recent MEM: 2-3 (vs OKC L, vs MIL W 21pt, vs UTAH W)
Recent PHI: 2-3 (vs OKC L 25pt, vs CHI L, vs DAL W)
Defense: MEM 101.8, PHI 110.9 (차이 9.1)
Pace: MEM 4/5 games > 220 total
```

**Step 2: Pattern Detection**
```python
patterns = {
    'defensive_mismatch': True,  # 9.1점 차이
    'h2h_dominance': True,       # MEM 3-1
    'blowout_tendency': True,    # MEM vs MIL 21pt
    'pace_differential': True    # MEM 고속 vs PHI 평균
}
```

**Step 3: Conditional Queries**
```
✅ defensive_mismatch → Query: MEM 수비 시스템 상세
✅ h2h_dominance → Query: H2H 각 경기 쿼터별 득점
✅ blowout_tendency → Query: MEM 블로우아웃 승리의 공통점
```

**Step 4: Rich Context 생성**
```
최종 컨텍스트 크기: ~3000 토큰
- Core data: 1500 토큰
- Conditional data: 1500 토큰
- 전체 15,433 노드 중 사용: ~200 노드 (1.3%)
```

---

## 비용 & 토큰 효율

### 모든 데이터 접근 (나쁜 예)
```
15,433 nodes × 평균 50 토큰 = 771,650 토큰
→ 입력 한도 초과 (대부분 LLM 128k 한도)
```

### Smart Graph RAG (좋은 예)
```
Core: 10 queries × 평균 100 토큰 = 1,000 토큰
Conditional: 3 queries × 평균 500 토큰 = 1,500 토큰
총 2,500 토큰 (효율 99.7% 개선!)
```

---

## 결론

**진짜 Graph RAG = 똑똑한 쿼리 선택**

1. **Core Queries**: 항상 실행 (10개 고정)
2. **Pattern Detection**: Core 결과 분석
3. **Conditional Queries**: 패턴에 따라 추가 쿼리
4. **Rich Context**: 관련성 높은 데이터만 집중

→ **결과: Neo4j의 0.1-1%만 쿼리하지만, 95% 인사이트 도출**

---

## Next Steps

1. **지금 (수동)**: Claude Code로 매일 분석
2. **관찰**: 어떤 패턴에서 어떤 쿼리를 쓰는지 기록
3. **코드화**: `SmartGraphRAG` 클래스 구현
4. **자동화**: VPS에서 매일 자동 실행
