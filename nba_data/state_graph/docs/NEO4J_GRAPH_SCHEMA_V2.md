# Neo4j Graph Schema V2 - Tactical & Contextual Analysis
**NBA State Graph - Phase 3 확장**

전술, 상성, 트렌드 분석을 위한 Graph DB 설계

---

## 🎯 설계 철학

**왜 정량 모델은 실패하고 Graph는 성공하는가?**

- **정량 모델**: 숫자만 보면 맥락을 잃음 (ELO, 승률, 득점 차이)
- **State Graph**: 상태 = 맥락 보존 + 관계가 살아있음
- **Graph RAG**: "비슷한 상황"을 찾아서 맥락 기반 예측

---

## 📊 노드 타입 (Node Types)

### 1. 기존 노드 (Phase 1)

```cypher
// 기본 엔티티
(:Team {abbr, name, conference, division})
(:Player {name, position, team_abbr})
(:Referee {name})

// 게임 상태
(:GameState {
  game_id, date, season,
  home_team, away_team,
  home_rest_days, away_rest_days,
  home_injuries: [], away_injuries: [],
  referees: [],
  result: {home_win, point_diff}
})
```

### 2. 전술 & 플레이 스타일 (NEW)

```cypher
// 팀 전술
(:Tactic {
  name: "Gap Defense" | "No-Pick Roll Play" | "Inside Spacing" | "20-30min Rotation",
  category: "defense" | "offense" | "rotation",
  team_abbr: "OKC" | "MIA" | "HOU" | "SA",
  description: "상세 설명",
  effectiveness: 0.78,  // 최근 효과성 지수
  sample_size: 50       // 분석 샘플 수
})

// 플레이 스타일
(:PlayStyle {
  name: "3-Point Heavy" | "Paint Dominant" | "Pace & Space",
  team_abbr: "BOS" | "HOU" | "GS",
  three_point_rate: 0.42,
  paint_points_pct: 0.35,
  pace: 102.5
})

// 전술 변화 (시즌 중 진화)
(:TacticEvolution {
  tactic_name: "20-30min Rotation",
  team_abbr: "SA",
  month: "2024-12",
  win_rate: 0.73,
  avg_fatigue_index: 0.45,  // 낮을수록 좋음
  wembanyama_minutes: 28.5
})
```

### 3. 매치업 & 상성 (NEW)

```cypher
// 팀 간 매치업 히스토리
(:MatchupHistory {
  team_a: "OKC",
  team_b: "MIA",
  season: "2024-25",
  wins_a: 2,
  wins_b: 1,
  avg_point_diff: +5.3,

  // 전술 상성
  tactic_a: "Gap Defense",
  tactic_b: "No-Pick Roll Play",
  tactic_b_success_rate: 0.67  // MIA가 OKC 갭 디펜스를 깬 확률
})

// 선수 대 선수 매치업
(:PlayerMatchup {
  player_a: "Wembanyama",
  player_b: "Jokic",
  games: 5,
  player_a_avg_pts: 22.4,
  player_b_avg_pts: 28.6,
  player_a_defensive_rating: 98.2
})
```

### 4. 선수 폼 & 트렌드 (NEW)

```cypher
// 선수 폼 지수 (시계열)
(:PlayerForm {
  player_name: "Wembanyama",
  date: "2024-12-23",
  period: "last_10_games",

  // 폼 지수
  form_index: 0.82,  // 0-1, 최근 10경기 평균 대비
  pts_avg: 24.5,
  reb_avg: 11.2,
  blk_avg: 3.8,

  // 상태
  injury_status: "healthy" | "questionable" | "out",
  games_played_last_7d: 3,
  minutes_load: 165  // 최근 7일 누적 분
})

// 리그 트렌드
(:LeagueTrend {
  name: "3-Point Revolution Reversal",
  season: "2024-25",
  description: "인사이드 스페이싱과 미드레인지 회귀",
  teams_affected: ["HOU", "SA", "DEN"],
  avg_3pt_rate: 0.36,  // 리그 평균
  trend_direction: "decreasing"
})
```

### 5. 심판 & 맥락 효과 (ENHANCED)

```cypher
// 심판 프로필 (확장)
(:Referee {
  name: "Scott Foster",

  // 기본 통계
  home_win_rate: 0.58,
  games_officiated: 234,

  // 스타일
  foul_call_rate: 42.5,      // 경기당 파울 수
  technical_foul_rate: 0.3,  // 경기당 테크니컬
  variance: 0.15,            // 판정 일관성 (낮을수록 일관적)

  // 특정 팀 효과
  okc_home_win_rate: 0.75,   // OKC 홈경기 승률
  mia_road_win_rate: 0.45    // MIA 원정 승률
})

// B2B & 휴식일 효과 (패턴화)
(:RestPattern {
  team: "SA",
  rest_days: 2,
  season: "2024-25",
  win_rate: 0.647,
  avg_point_diff: +6.8,
  rotation_tactic_effectiveness: 0.89  // 로테이션 효과 극대화
})
```

---

## 🔗 관계 타입 (Relationships)

### 1. 전술 & 상성

```cypher
// 팀-전술 사용
(Team)-[:USES_TACTIC {
  start_date: "2024-10-22",
  frequency: 0.85,          // 얼마나 자주 사용하나
  success_rate: 0.73
}]->(Tactic)

// 전술-전술 카운터
(Tactic)-[:COUNTERS {
  effectiveness: 0.67,      // 67% 확률로 카운터
  sample_games: 15,
  avg_point_swing: +8.5     // 카운터 성공 시 평균 점수차
}]->(Tactic)

// 전술-선수 의존성
(Tactic)-[:REQUIRES_PLAYER {
  role: "Rim Protector" | "Floor Spacer" | "Primary Ball Handler",
  importance: 0.9           // 해당 선수 없으면 효과 90% 감소
}]->(Player)

// 전술-플레이스타일 효과
(Tactic)-[:EFFECTIVE_VS {
  win_rate: 0.78,
  sample_games: 20
}]->(PlayStyle)
```

### 2. 매치업 & 상태

```cypher
// 팀-팀 매치업
(Team)-[:MATCHUP_VS {
  season: "2024-25",
  wins: 3,
  losses: 1,
  avg_rest_advantage: +1.5,  // 평균 휴식일 차이
  tactic_clash: "Gap Defense vs No-Pick Roll"
}]->(Team)

// 선수-선수 매치업
(Player)-[:DEFENDS_AGAINST {
  defensive_rating: 102.5,
  opponent_fg_pct: 0.38,
  games: 12
}]->(Player)

// 게임-전술 특징
(GameState)-[:FEATURED_TACTIC {
  tactic_success: true,
  impact_on_result: 0.8      // 승패에 미친 영향도
}]->(Tactic)
```

### 3. 폼 & 트렌드

```cypher
// 선수-폼 상태
(Player)-[:IN_FORM {
  period: "last_10_games",
  form_index: 0.82,
  peak_date: "2024-12-20"
}]->(PlayerForm)

// 팀-트렌드 참여
(Team)-[:FOLLOWS_TREND {
  adoption_date: "2024-11-15",
  effectiveness: 0.76
}]->(LeagueTrend)

// 게임-상황 컨텍스트
(GameState)-[:HAS_CONTEXT {
  b2b: true,
  rest_advantage: +2,
  injury_impact: "high",
  referee_bias: "home",
  tactic_matchup: "favorable"
}]->(GameState)  // self-reference for context embedding
```

---

## 🔍 핵심 쿼리 시나리오

### 시나리오 1: OKC vs MIA 전술 분석

```cypher
// OKC 갭 디펜스가 MIA 노-픽 롤플레이에 당할 확률
MATCH (okc:Team {abbr: "OKC"})-[:USES_TACTIC]->(gapDef:Tactic {name: "Gap Defense"})
MATCH (mia:Team {abbr: "MIA"})-[:USES_TACTIC]->(noPick:Tactic {name: "No-Pick Roll Play"})
MATCH (noPick)-[counter:COUNTERS]->(gapDef)

OPTIONAL MATCH (okc)-[matchup:MATCHUP_VS]->(mia)
WHERE matchup.season = "2024-25"

RETURN
  counter.effectiveness AS counter_rate,
  counter.avg_point_swing AS point_impact,
  matchup.wins AS okc_wins,
  matchup.losses AS okc_losses,
  matchup.tactic_clash AS clash_history
```

### 시나리오 2: 샌안 로테이션 시즌 진화

```cypher
// 웸반야마 + 로테이션의 월별 성장
MATCH (sa:Team {abbr: "SA"})-[:USES_TACTIC]->(rotation:Tactic {name: "20-30min Rotation"})
MATCH (evolution:TacticEvolution {tactic_name: "20-30min Rotation"})
WHERE evolution.team_abbr = "SA"

MATCH (wemby:Player {name: "Wembanyama"})-[:IN_FORM]->(form:PlayerForm)
WHERE form.period = "last_10_games"

WITH evolution, form
ORDER BY evolution.month

RETURN
  evolution.month,
  evolution.win_rate,
  evolution.avg_fatigue_index,
  evolution.wembanyama_minutes,
  form.form_index AS wembanyama_form
```

### 시나리오 3: 휴스턴 인사이드 스페이싱 효과

```cypher
// 센군/아담스 조합 시 오펜스 효율
MATCH (hou:Team {abbr: "HOU"})-[:USES_TACTIC]->(spacing:Tactic {name: "Inside Spacing"})
MATCH (spacing)-[:REQUIRES_PLAYER {role: "Floor Spacer"}]->(sengun:Player {name: "Sengun"})
MATCH (spacing)-[:REQUIRES_PLAYER {role: "Rim Protector"}]->(adams:Player {name: "Adams"})

MATCH (game:GameState)
WHERE (game.home_team = "HOU" OR game.away_team = "HOU")
  AND sengun.name IN game.home_lineup OR sengun.name IN game.away_lineup
  AND adams.name IN game.home_lineup OR adams.name IN game.away_lineup

WITH game,
     CASE WHEN game.home_team = "HOU" THEN game.result.home_win ELSE NOT game.result.home_win END AS hou_win,
     game.result.point_diff AS point_diff

RETURN
  count(*) AS games_with_combo,
  sum(CASE WHEN hou_win THEN 1 ELSE 0 END) * 1.0 / count(*) AS win_rate,
  avg(point_diff) AS avg_point_diff,
  "3점 적지만 오펜스 효율 극대화" AS note
```

### 시나리오 4: AI 매치업 리포트 생성

```cypher
// 12/25 LAL vs BOS 종합 분석
MATCH (lal:Team {abbr: "LAL"}), (bos:Team {abbr: "BOS"})

// 1. 과거 매치업
OPTIONAL MATCH (lal)-[matchup:MATCHUP_VS]->(bos)
WHERE matchup.season = "2024-25"

// 2. 현재 폼
OPTIONAL MATCH (lal)-[:HAS_PLAYER]->(lalPlayer:Player)-[:IN_FORM]->(lalForm:PlayerForm)
WHERE lalForm.period = "last_10_games"

OPTIONAL MATCH (bos)-[:HAS_PLAYER]->(bosPlayer:Player)-[:IN_FORM]->(bosForm:PlayerForm)
WHERE bosForm.period = "last_10_games"

// 3. 전술 상성
OPTIONAL MATCH (lal)-[:USES_TACTIC]->(lalTactic:Tactic)
OPTIONAL MATCH (bos)-[:USES_TACTIC]->(bosTactic:Tactic)
OPTIONAL MATCH (lalTactic)-[counter:COUNTERS]->(bosTactic)

// 4. B2B & 휴식
MATCH (game:GameState {date: "2024-12-25", home_team: "BOS", away_team: "LAL"})

RETURN {
  matchup_history: {
    lal_wins: matchup.wins,
    bos_wins: matchup.losses,
    avg_diff: matchup.avg_point_diff
  },
  current_form: {
    lal_form_avg: avg(lalForm.form_index),
    bos_form_avg: avg(bosForm.form_index)
  },
  tactic_clash: {
    lal_tactic: lalTactic.name,
    bos_tactic: bosTactic.name,
    counter_effectiveness: counter.effectiveness
  },
  game_context: {
    bos_rest_days: game.home_rest_days,
    lal_rest_days: game.away_rest_days,
    rest_advantage: game.home_rest_days - game.away_rest_days,
    referees: game.referees,
    injuries: game.home_injuries + game.away_injuries
  }
} AS matchup_report
```

---

## 🚀 Graph RAG 설계

### RAG 파이프라인

```
사용자 질문: "OKC vs MIA, B2B, Scott Foster 배정되면?"

1. Query Embedding (벡터화)
   → "OKC", "MIA", "B2B", "Scott Foster" 키워드 추출

2. Graph Traversal (Cypher)
   → MATCH (okc:Team {abbr: "OKC"})-[:USES_TACTIC]->(tactic)
   → MATCH (game:GameState {home_team: "OKC", away_team: "MIA"})
   → WHERE "Scott Foster" IN game.referees AND game.home_rest_days = 0

3. Context Gathering
   → 과거 10경기 유사 상황
   → 전술 상성
   → 심판 효과
   → B2B 패턴

4. LLM Generation
   → 맥락 기반 분석 리포트 생성
```

### 벡터 인덱스 (Neo4j)

```cypher
// 게임 상태 임베딩
CREATE VECTOR INDEX game_state_embedding
FOR (g:GameState)
ON g.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}

// 전술 임베딩
CREATE VECTOR INDEX tactic_embedding
FOR (t:Tactic)
ON t.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}
```

---

## 💎 프리미엄 기능 설계

### 1. Graph Viewer

```
Interactive UI:
- 팀 클릭 → 사용 전술 시각화
- 전술 클릭 → 카운터 전술 네트워크
- 게임 클릭 → 전체 컨텍스트 (부상, 심판, B2B, 전술)
- 선수 클릭 → 폼 지수 차트 + 매치업 히스토리

기술 스택:
- Neo4j Browser (커스터마이징)
- React + D3.js (커스텀 뷰어)
- Graph Data Science Library (중심성, 커뮤니티 감지)
```

### 2. Trend Detection

```cypher
// 자동 트렌드 감지
MATCH (team:Team)-[:USES_TACTIC]->(tactic:Tactic)
MATCH (evolution:TacticEvolution {tactic_name: tactic.name})
WHERE evolution.month >= "2024-11"

WITH tactic, collect(evolution.win_rate) AS monthly_rates
WHERE size(monthly_rates) >= 3

WITH tactic,
     monthly_rates[-1] - monthly_rates[0] AS trend_change,
     monthly_rates

WHERE trend_change > 0.15  // 15% 이상 상승

RETURN tactic.name AS trending_tactic,
       tactic.team_abbr AS team,
       trend_change AS growth_rate,
       "🔥 HOT TREND" AS alert
```

---

## 📅 마이그레이션 계획

### Phase 3A: 데이터 수집
1. 전술 태깅 (Manual + AI 보조)
2. 플레이 스타일 분류
3. 선수 폼 지수 계산

### Phase 3B: Graph 구축
1. Supabase → Neo4j 마이그레이션
2. 관계 생성 (COUNTERS, EFFECTIVE_VS)
3. 벡터 임베딩 생성

### Phase 3C: RAG 엔진
1. Cypher 쿼리 템플릿 작성
2. LLM 통합 (Claude/GPT-4)
3. 리포트 생성 파이프라인

### Phase 3D: 프리미엄 서비스
1. Graph Viewer 개발
2. 트렌드 알림 시스템
3. 유료 구독 모델 (월 10만원)

---

**Made with ❤️ by State Graph Engine**
*"정량은 What, Graph는 Why"*
