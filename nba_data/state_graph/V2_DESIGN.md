# NBA 베팅 분석 시스템 v2.0 설계

## 핵심 철학: 팀은 구성 요소의 합

```
Team ≠ 고정된 엔티티
Team = Coach + Players + Lineups + Context
```

### 기존(v1.1) 문제점

```
❌ "HOU 백투백 홈: 70%"
   → Durant 트레이드? 여전히 70%?
   → Udoka 경질? 여전히 70%?
   → Adams 부상? 여전히 70%?

❌ 팀 단위 분석 = 변화에 취약
❌ 왜? 라는 질문에 답 불가
❌ 시즌마다 전부 재학습 필요
```

### v2.0 접근

```
✅ Coach 성향 분석 (템포, 로테이션)
✅ Player 개인 Impact
✅ Player IN/OUT 효과
✅ 핵심 Lineup (수동 입력)
✅ 동적 팀 계산

→ 변화에 즉시 대응!
→ 인과 관계 명확!
```

---

## 스키마 설계

### 1. Coach 노드 (자동 계산)

```cypher
CREATE (coach:Coach {
  name: "Ime Udoka",
  team: "HOU",
  season: "2025-26",

  // 로테이션 패턴 (PlayerBoxScore에서 계산)
  rotation_depth: 9.2,          // 평균 20분+ 선수 수
  avg_starter_minutes: 34.8,    // 주전(30분+) 평균 출전
  avg_bench_minutes: 15.2,      // 벤치 평균 출전

  // 템포 (possessions per game)
  tempo: 99.5,                  // 팀 템포 = 코치 템포
  pace_rank: 12,                // 리그 순위

  // 신뢰도 (계산)
  rookie_trust: 0.3,            // 루키 평균 출전 시간 / 주전
  veteran_bias: 0.8,            // 베테랑 우대

  // 메타
  games_coached: 28,
  win_pct: 0.667
})
```

**계산 방법:**
```python
def calculate_coach_stats(team, season='2025-26'):
    """PlayerBoxScore에서 코치 성향 자동 계산"""
    query = """
    MATCH (pb:PlayerBoxScore {team: $team})
    WHERE pb.date >= date('2025-10-01')
    WITH pb.date AS game,
         collect({name: pb.player_name, min: pb.minutes}) AS players
    RETURN
      avg(size([p IN players WHERE p.min > 20])) AS rotation_depth,
      avg([p IN players WHERE p.min > 30 | p.min][0]) AS starter_minutes,
      avg([p IN players WHERE p.min < 20 | p.min][0]) AS bench_minutes
    """

    # Tempo 계산 (possessions ≈ FGA + 0.44*FTA + TO - ORB)
    # 또는 간단히: (Team Pace + Opp Pace) / 2
```

### 2. Player 노드 (확장)

```cypher
CREATE (player:Player {
  name: "Steven Adams",
  player_id: "6609",
  team: "HOU",
  position: "C",

  // Impact (PlayerBoxScore에서 계산)
  avg_plus_minus: 7.1,          // 평균 +/-
  impact_percentile: 0.78,      // 리그 내 순위

  // Usage
  avg_minutes: 18.1,            // 평균 출전
  games_played: 24,
  games_missed: 2,
  injury_prone: 0.08,           // 결장 비율

  // Style (PlayerBoxScore 통계 기반)
  ppg: 5.2,
  rpg: 7.3,
  apg: 1.1,
  oreb_pg: 3.8,                 // 정성→정량!

  style_tags: ["rim-protector", "screen-setter", "oreb-specialist"],

  // 체력
  stamina: 0.95,                // 백투백 +/- 하락폭으로 계산

  // 메타
  season: "2025-26"
})
```

**계산 방법:**
```python
def calculate_player_impact(player_name, team):
    """PlayerBoxScore에서 선수 속성 계산"""
    query = """
    MATCH (pb:PlayerBoxScore {player_name: $name, team: $team})
    WHERE pb.date >= date('2025-10-01')
    RETURN
      avg(pb.plus_minus) AS impact,
      avg(pb.minutes) AS avg_minutes,
      avg(pb.points) AS ppg,
      avg(pb.rebounds) AS rpg,
      avg(pb.assists) AS apg,
      avg(pb.off_rebounds) AS oreb_pg,
      count(*) AS games_played
    """

    # 백투백 stamina 계산
    b2b_query = """
    MATCH (g1:GameState)-[:HAS_BOXSCORE]->(pb1:PlayerBoxScore {player_name: $name})
    MATCH (g2:GameState)-[:HAS_BOXSCORE]->(pb2:PlayerBoxScore {player_name: $name})
    WHERE g2.date = g1.date + duration('P1D')
    RETURN avg(pb2.plus_minus - pb1.plus_minus) AS fatigue_drop
    """
    # stamina = 1 - (abs(fatigue_drop) / 10)
```

### 3. Lineup 노드 (수동 입력)

```cypher
CREATE (lineup:Lineup {
  lineup_id: "HOU_starting_5",
  team: "HOU",
  name: "Starting 5",

  // 구성
  players: ["Kevin Durant", "Alperen Sengun", "Klay Thompson",
            "Fred VanVleet", "Dillon Brooks"],
  player_count: 5,

  // 사용 빈도 (수동 입력)
  usage_pct: 35,                // 전체 시간의 35%
  typical_minutes: 28,          // 평균 함께 뛰는 시간

  // 특징 (수동 입력)
  style: "balanced",
  tempo_boost: 1.0,             // 템포 조정 (1.0 = 중립)
  defense_rating: 0.9,          // 수비 강도
  offense_rating: 1.1,          // 공격 강도

  // 메타
  notes: "주력 라인업, 밸런스형",
  season: "2025-26"
})

// 관계
MATCH (lineup:Lineup {lineup_id: "HOU_starting_5"})
MATCH (p:Player {name: "Kevin Durant"})
CREATE (lineup)-[:INCLUDES {role: "primary-scorer"}]->(p)
```

**수동 입력 형식 (lineups.json):**
```json
{
  "HOU": {
    "coach": "Ime Udoka",
    "lineups": [
      {
        "name": "Starting 5",
        "players": ["Kevin Durant", "Alperen Sengun", "Klay Thompson",
                    "Fred VanVleet", "Dillon Brooks"],
        "usage_pct": 35,
        "style": "balanced",
        "tempo_boost": 1.0,
        "notes": "주력 라인업"
      },
      {
        "name": "Big Lineup",
        "players": ["Kevin Durant", "Alperen Sengun", "Steven Adams",
                    "Fred VanVleet", "Dillon Brooks"],
        "usage_pct": 15,
        "style": "defensive",
        "tempo_boost": 0.95,
        "notes": "수비 중심, Adams 스크린"
      }
    ]
  }
}
```

### 4. GameContext 노드 (동적 생성)

```cypher
CREATE (ctx:GameContext {
  game_id: "401810XXX",
  date: date('2025-12-27'),

  // 팀별 컨텍스트
  home_team: "HOU",
  away_team: "NYK",
  home_rest_days: 1,
  away_rest_days: 0,
  home_back_to_back: false,
  away_back_to_back: true,

  // 외부 요인
  referee_home_bias: 0.52,
  altitude: 0,

  // 부상자 (ESPN 프리뷰에서)
  home_injuries: ["Player A", "Player B"],
  away_injuries: ["Player C"]
})
```

---

## 동적 팀 계산 엔진

### Team 노드는 존재하지 않음!
**쿼리 시점에 실시간 계산**

```python
def calculate_team_strength(team: str, context: GameContext, lineup_name: str = "Starting 5"):
    """
    팀 강도 = Coach + Players + Lineup + Context
    """

    # 1. Coach 기본값
    coach = get_coach(team)
    base_tempo = coach.tempo
    rotation_fatigue = coach.rotation_depth / 10  # 로테이션 깊을수록 피로 적음

    # 2. Lineup 선택
    lineup = get_lineup(team, lineup_name)
    players = [get_player(name) for name in lineup.players]

    # 3. Player Impact 합산
    total_impact = sum(p.avg_plus_minus for p in players)

    # 4. Lineup 시너지 (사용자 입력)
    lineup_bonus = lineup.offense_rating * 5  # 간단한 가중치

    # 5. Context 조정
    context_mod = 0

    # 백투백 페널티
    if context.back_to_back:
        # 로테이션 깊이에 따라 페널티 달라짐
        fatigue_penalty = -15 * (1 - rotation_fatigue)

        # 선수별 stamina 고려
        stamina_avg = sum(p.stamina for p in players) / len(players)
        fatigue_penalty *= (2 - stamina_avg)

        context_mod += fatigue_penalty

    # 홈 어드밴티지
    if context.home:
        context_mod += 3
        if context.referee_home_bias > 0.55:
            context_mod += 2

    # 6. 부상자 영향
    injury_penalty = 0
    for injured_player in context.injuries:
        p = get_player(injured_player)
        if p:
            injury_penalty -= p.avg_plus_minus

    # 7. 템포 조정
    tempo_factor = (base_tempo * lineup.tempo_boost - 100) * 0.3

    # 최종 계산
    team_strength = (
        total_impact +          # 선수 개인 능력
        lineup_bonus +          # 라인업 시너지
        context_mod +           # 백투백, 홈, 심판
        injury_penalty +        # 부상자
        tempo_factor            # 템포
    )

    return {
        'strength': team_strength,
        'breakdown': {
            'player_impact': total_impact,
            'lineup_bonus': lineup_bonus,
            'context': context_mod,
            'injuries': injury_penalty,
            'tempo': tempo_factor
        }
    }
```

---

## 사용 예시

### 예시 1: Adams 부상 시뮬레이션

```python
# 정상 HOU
hou_normal = calculate_team_strength(
    team="HOU",
    context=GameContext(back_to_back=True),
    lineup_name="Big Lineup"  # Adams 포함
)
# Strength: 88.5
# - Durant: +12.5
# - Sengun: +8.2
# - Adams: +7.1
# - VanVleet: +5.8
# - Brooks: +3.2
# - Lineup bonus: +6 (defensive)
# - B2B penalty: -8 (rotation 9명)
# = 42.8

# Adams 부상 → Starting 5로 변경
hou_injured = calculate_team_strength(
    team="HOU",
    context=GameContext(back_to_back=True),
    lineup_name="Starting 5"  # Thompson으로 교체
)
# Strength: 82.1
# - Adams: -7.1
# + Thompson: +6.2
# - Lineup bonus: +9 (balanced) → +6 (defensive 손실)
# = 35.5

# 예측: -7 strength → 승률 -12%p
```

### 예시 2: 코치 비교

```python
# HOU (Udoka)
udoka_team = calculate_team_strength(
    team="HOU",
    context=GameContext(back_to_back=True)
)
# B2B penalty: -8% (rotation 9명)

# NYK (Thibs)
thibs_team = calculate_team_strength(
    team="NYK",
    context=GameContext(back_to_back=True)
)
# B2B penalty: -15% (rotation 7명, 주전 혹사!)
```

### 예시 3: Lineup 전략

```python
# HOU vs slow team (템포 느림)
slow_matchup = calculate_team_strength(
    team="HOU",
    lineup_name="Big Lineup"  # tempo_boost: 0.95
)
# 템포 느림 → 득점 -3점

# HOU vs fast team (템포 빠름)
fast_matchup = calculate_team_strength(
    team="HOU",
    lineup_name="Small Ball"  # tempo_boost: 1.10
)
# 템포 빠름 → 득점 +5점
```

---

## 마이그레이션 계획

### Phase 1: 병렬 운영 (1주)
```
v1.1 (기존): 팀 단위 baseline
  → "HOU 백투백: 70%"

v2.0 (신규): 구성 요소 기반
  → Coach + Players + Lineup

→ 두 시스템 동시 실행, 정확도 비교
```

### Phase 2: 검증 (1주)
```
과거 경기로 백테스팅:
- v1.1 예측 vs v2.0 예측
- 실제 결과 비교
- 어느 쪽이 더 정확한가?
```

### Phase 3: 전환 (1주)
```
v2.0이 우수하면:
- v1.1 deprecated
- v2.0을 main으로
- 일일 보고서 통합
```

---

## 포기하는 것 (명시)

```
❌ FrontOffice 전략
   → 정성적, 자동화 불가
   → ROI 낮음

❌ 모든 lineup 조합
   → API 불안정
   → 핵심 3-5개만 수동 입력

❌ 선수 간 정밀 시너지
   → NBA Stats API 필요
   → 근사치로 대체 (IN/OUT 비교)

❌ 코치 철학/성향
   → 주관적
   → 통계로 유추 가능한 것만 (템포, 로테이션)
```

---

## 데이터 흐름

```
1. 매일 자동
   └─ update_yesterday_games.py (v2.0)
      ├─ GameState 추가
      ├─ PlayerBoxScore 추가
      └─ Coach 노드 업데이트 (재계산)

2. 주 1회 (시즌 중 변화 시)
   └─ lineups.json 수동 업데이트
      - 부상자 변경
      - 트레이드 반영
      - 로테이션 변화

3. 경기 분석 시
   └─ calculate_team_strength()
      - 실시간 계산
      - Team 노드 없음
      - 모든 요소 합산
```

---

## 성공 기준

```
✅ Adams 부상 → 즉시 -12%p 예측 가능
✅ Durant 트레이드 → 즉시 -15 strength 계산
✅ 코치 교체 → 템포/로테이션 자동 조정
✅ 백투백 → 로테이션 깊이별 차등 페널티
✅ "왜?" 질문에 답 가능
   - "왜 HOU가 백투백에 강한가?"
   - → Udoka 9-man rotation + Sengun playmaking
```

---

## 다음 단계

1. **Coach 생성 스크립트** (자동 계산)
2. **Lineup 임포터** (JSON → Neo4j)
3. **Player 속성 확장** (impact, style)
4. **동적 계산 엔진** (calculate_team_strength)
5. **백테스팅** (v1.1 vs v2.0)
