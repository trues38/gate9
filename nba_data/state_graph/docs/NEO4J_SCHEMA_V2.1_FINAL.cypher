// ============================================================================
// NBA State Graph - Neo4j Schema V2.1 FINAL
// ============================================================================
// 피드백 7개 전부 반영 + 실행 가능 버전
// "정량은 What, Graph는 Why"
// ============================================================================

// ============================================================================
// CONSTRAINTS & INDEXES
// ============================================================================

// 팀
CREATE CONSTRAINT team_abbr IF NOT EXISTS FOR (t:Team) REQUIRE t.abbr IS UNIQUE;
CREATE INDEX team_name IF NOT EXISTS FOR (t:Team) ON (t.name);

// 선수
CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.player_id IS UNIQUE;
CREATE INDEX player_name IF NOT EXISTS FOR (p:Player) ON (p.name);

// 심판
CREATE CONSTRAINT referee_name IF NOT EXISTS FOR (r:Referee) REQUIRE r.name IS UNIQUE;

// 게임 상태
CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:GameState) REQUIRE g.game_id IS UNIQUE;
CREATE INDEX game_date IF NOT EXISTS FOR (g:GameState) ON (g.date);
CREATE INDEX game_season IF NOT EXISTS FOR (g:GameState) ON (g.season);

// 전술 (팀별로 같은 이름 가능하므로 composite key)
CREATE CONSTRAINT tactic_composite IF NOT EXISTS
FOR (t:Tactic) REQUIRE (t.name, t.origin_team) IS UNIQUE;

// 선수 폼
CREATE INDEX form_date IF NOT EXISTS FOR (f:PlayerForm) ON (f.date);
CREATE INDEX form_player IF NOT EXISTS FOR (f:PlayerForm) ON (f.player_name);

// ============================================================================
// VECTOR INDEX (GameState only - 초기 버전)
// ============================================================================

CREATE VECTOR INDEX game_state_embedding IF NOT EXISTS
FOR (g:GameState)
ON g.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};

// ============================================================================
// NODE SCHEMAS
// ============================================================================

// ----------------------------------------------------------------------------
// 1. 기본 엔티티
// ----------------------------------------------------------------------------

// 팀
(:Team {
  abbr: STRING,              // "OKC"
  name: STRING,              // "Oklahoma City Thunder"
  conference: STRING,        // "West"
  division: STRING,          // "Northwest"

  // 계산용 필드
  current_win_rate: FLOAT,   // 0.73
  current_form_index: FLOAT  // 최근 10경기 폼
})

// 선수
(:Player {
  player_id: STRING,         // ESPN player ID
  name: STRING,              // "Victor Wembanyama"
  position: STRING,          // "C"

  // 설명용 필드
  height: STRING,            // "7-4"

  // 계산용 필드
  career_ppg: FLOAT,
  career_rpg: FLOAT
})

// 심판 (Enhanced)
(:Referee {
  name: STRING,              // "Scott Foster"

  // 계산용 통계
  home_win_rate: FLOAT,      // 0.58
  games_officiated: INTEGER, // 234

  // 스타일 (계산용)
  foul_call_rate: FLOAT,     // 42.5 (경기당 파울 수)
  technical_foul_rate: FLOAT,// 0.3 (경기당 테크니컬)
  variance: FLOAT,           // 0.15 (판정 일관성, 낮을수록 일관적)

  // 특정 팀 효과 (계산용) - 관계로도 표현 가능
  team_bias: MAP             // {OKC: 0.75, MIA: 0.45}
})

// ----------------------------------------------------------------------------
// 2. 게임 상태 (핵심)
// ----------------------------------------------------------------------------

(:GameState {
  game_id: STRING,           // "401810220"
  date: DATE,                // 2024-12-16
  season: STRING,            // "2024-25"

  // 팀 정보
  home_team: STRING,         // "MIN"
  away_team: STRING,         // "PHX"

  // 휴식일 (계산용)
  home_rest_days: INTEGER,   // 1
  away_rest_days: INTEGER,   // 2

  // 부상자 (설명용)
  home_injuries: LIST<STRING>,  // ["Mike Conley - Day-To-Day"]
  away_injuries: LIST<STRING>,  // ["Kevin Durant - Out"]

  // 심판 (설명용, 관계로도 표현)
  referees: LIST<STRING>,    // ["Scott Foster", "Tony Brothers"]

  // 결과 (계산용)
  result: {
    home_win: BOOLEAN,
    home_points: INTEGER,
    away_points: INTEGER,
    point_diff: INTEGER      // home - away
  },

  // 벡터 임베딩 (RAG용)
  embedding: VECTOR<FLOAT>[768],

  // 맥락 점수 (계산용)
  context_score: {
    rest_advantage: INTEGER,      // home_rest - away_rest
    injury_impact: FLOAT,         // 0.0 ~ 1.0
    referee_bias: FLOAT,          // -1.0 ~ 1.0 (음수면 원정 유리)
    tactic_favorability: FLOAT    // -1.0 ~ 1.0
  }
})

// 👉 LINEUP은 배열이 아니라 관계로! (피드백 4)
// (GameState)-[:STARTED]->(Player)
// (GameState)-[:PLAYED {minutes: 32}]->(Player)

// ----------------------------------------------------------------------------
// 3. 전술 & 플레이스타일
// ----------------------------------------------------------------------------

(:Tactic {
  name: STRING,              // "Gap Defense"
  origin_team: STRING,       // "OKC" (최초 개발팀, 소속 아님!)
  category: STRING,          // "defense" | "offense" | "rotation"

  // 설명용 필드
  description: STRING,       // "드라이브 레인에 디펜더 배치..."

  // 계산용 필드
  effectiveness: FLOAT,      // 0.78 (최근 효과성)
  sample_size: INTEGER,      // 50

  // 통계적 시그니처 (계산용)
  statistical_signature: {
    opponent_paint_points_max: FLOAT,  // < 40
    steals_per_game_min: FLOAT,        // > 10
    // ... 기타 지표
  }
})
// 👉 team_abbr 제거! 소속은 USES_TACTIC 관계로만 (피드백 2)

(:PlayStyle {
  name: STRING,              // "3-Point Heavy"

  // 설명용
  description: STRING,

  // 계산용
  three_point_rate: FLOAT,   // 0.42
  paint_points_pct: FLOAT,   // 0.35
  pace: FLOAT                // 102.5
})

(:TacticEvolution {
  tactic_name: STRING,
  team_abbr: STRING,
  month: STRING,             // "2024-12"

  // 계산용
  win_rate: FLOAT,           // 0.73
  avg_fatigue_index: FLOAT,  // 0.45 (낮을수록 좋음)
  sample_games: INTEGER
})

// ----------------------------------------------------------------------------
// 4. 선수 폼 & 트렌드
// ----------------------------------------------------------------------------

(:PlayerForm {
  player_name: STRING,
  date: DATE,                // 2024-12-23
  period: STRING,            // "last_10_games"

  // 계산용 지표
  form_index: FLOAT,         // 0.82 (0-1)
  pts_avg: FLOAT,
  reb_avg: FLOAT,
  blk_avg: FLOAT,

  // 상태 (계산용)
  injury_status: STRING,     // "healthy" | "questionable" | "out"
  games_played_last_7d: INTEGER,
  minutes_load: INTEGER      // 최근 7일 누적 분
})

(:LeagueTrend {
  name: STRING,              // "3-Point Revolution Reversal"
  season: STRING,            // "2024-25"

  // 설명용
  description: STRING,

  // 계산용
  teams_affected: LIST<STRING>,
  avg_3pt_rate: FLOAT,
  trend_direction: STRING    // "increasing" | "decreasing" | "stable"
})

// ----------------------------------------------------------------------------
// 5. 컨텍스트 (옵션: self-edge 대신 노드 분리)
// ----------------------------------------------------------------------------

(:ContextSnapshot {
  // 계산용 필드만
  b2b: BOOLEAN,
  rest_advantage: INTEGER,
  injury_impact: FLOAT,
  referee_bias: FLOAT,
  tactic_matchup: STRING     // "favorable" | "neutral" | "unfavorable"
})
// 👉 초기엔 GameState.context_score로 시작하고,
//    나중에 필요시 분리 (피드백 5)

// ============================================================================
// RELATIONSHIP SCHEMAS
// ============================================================================

// ----------------------------------------------------------------------------
// 팀 관계
// ----------------------------------------------------------------------------

// 팀 → 선수
(Team)-[:HAS_PLAYER]->(Player)

// 팀 → 전술 (피드백 2: 이게 유일한 소속 표현)
(Team)-[:USES_TACTIC {
  start_date: DATE,          // 언제부터 사용했나
  end_date: DATE,            // NULL이면 현재 사용 중
  frequency: FLOAT,          // 0.85 (얼마나 자주 사용하나)
  success_rate: FLOAT        // 0.73
}]->(Tactic)

// 팀 → 플레이스타일
(Team)-[:ADOPTS_STYLE {
  season: STRING,
  fit_score: FLOAT           // 얼마나 잘 맞는지
}]->(PlayStyle)

// 팀 → 팀 매치업 (피드백 1: 노드가 아니라 관계!)
(Team)-[:MATCHUP {
  season: STRING,            // "2024-25"
  wins: INTEGER,             // 3
  losses: INTEGER,           // 1
  avg_point_diff: FLOAT,     // +5.3

  // 전술 충돌
  dominant_tactic: STRING,   // 이긴 쪽 전술
  countered_tactic: STRING,  // 진 쪽 전술

  // 계산용
  last_meeting_date: DATE,
  home_advantage: FLOAT      // 홈/원정 분리 시
}]->(Team)

// 팀 → 트렌드
(Team)-[:FOLLOWS_TREND {
  adoption_date: DATE,
  effectiveness: FLOAT       // 0.76
}]->(LeagueTrend)

// ----------------------------------------------------------------------------
// 전술 관계
// ----------------------------------------------------------------------------

// 전술 → 전술 카운터 (핵심!)
(Tactic)-[:COUNTERS {
  effectiveness: FLOAT,      // 0.67 (67% 확률로 카운터)
  sample_games: INTEGER,     // 15
  avg_point_swing: FLOAT,    // +8.5 (카운터 성공 시 평균 점수차)
  confidence: FLOAT          // 0.8 (통계적 신뢰도)
}]->(Tactic)

// 전술 → 선수 의존성 (피드백 3: absence_penalty로 명확화!)
(Tactic)-[:REQUIRES_PLAYER {
  role: STRING,              // "Rim Protector" | "Floor Spacer"
  absence_penalty: FLOAT,    // 0.9 (해당 선수 없으면 효과 90% 감소)
  min_minutes: INTEGER       // 최소 몇 분 이상 출전해야 하나
}]->(Player)

// 전술 → 플레이스타일 효과
(Tactic)-[:EFFECTIVE_VS {
  win_rate: FLOAT,           // 0.78
  sample_games: INTEGER      // 20
}]->(PlayStyle)

// ----------------------------------------------------------------------------
// 게임 관계 (피드백 4: LINEUP을 관계로!)
// ----------------------------------------------------------------------------

// 게임 → 선수 (라인업 표현)
(GameState)-[:STARTED {
  team: STRING,              // "home" | "away"
  position: STRING           // "PG" | "SG" | "SF" | "PF" | "C"
}]->(Player)

(GameState)-[:PLAYED {
  team: STRING,              // "home" | "away"
  minutes: INTEGER,          // 32
  points: INTEGER,
  plus_minus: INTEGER
}]->(Player)

// 게임 → 심판
(GameState)-[:OFFICIATED_BY]->(Referee)

// 게임 → 전술 (어떤 전술이 사용되었나)
(GameState)-[:FEATURED_TACTIC {
  team: STRING,              // "home" | "away"
  tactic_success: BOOLEAN,   // 전술이 먹혔나
  impact_on_result: FLOAT    // 0.8 (승패에 미친 영향도)
}]->(Tactic)

// 게임 → 컨텍스트 (옵션)
// (GameState)-[:HAS_CONTEXT]->(ContextSnapshot)
// 초기엔 GameState.context_score로 충분

// ----------------------------------------------------------------------------
// 선수 관계
// ----------------------------------------------------------------------------

// 선수 → 폼
(Player)-[:IN_FORM {
  period: STRING,            // "last_10_games"
  form_index: FLOAT,         // 0.82
  peak_date: DATE
}]->(PlayerForm)

// 선수 → 선수 매치업
(Player)-[:DEFENDS_AGAINST {
  season: STRING,
  defensive_rating: FLOAT,   // 102.5
  opponent_fg_pct: FLOAT,    // 0.38
  games: INTEGER             // 12
}]->(Player)

// ============================================================================
// 핵심 쿼리 예시
// ============================================================================

// ----------------------------------------------------------------------------
// 쿼리 1: OKC vs MIA 전술 분석
// ----------------------------------------------------------------------------

MATCH (okc:Team {abbr: "OKC"})-[:USES_TACTIC]->(gapDef:Tactic {name: "Gap Defense"})
MATCH (mia:Team {abbr: "MIA"})-[:USES_TACTIC]->(noPick:Tactic {name: "No-Pick Roll Play"})
MATCH (noPick)-[counter:COUNTERS]->(gapDef)

OPTIONAL MATCH (okc)-[matchup:MATCHUP {season: "2024-25"}]->(mia)

RETURN
  counter.effectiveness AS counter_rate,
  counter.avg_point_swing AS point_impact,
  matchup.wins AS okc_wins,
  matchup.losses AS mia_wins,
  matchup.dominant_tactic AS winning_tactic;

// ----------------------------------------------------------------------------
// 쿼리 2: 특정 경기의 라인업 효과 (피드백 4 적용)
// ----------------------------------------------------------------------------

MATCH (game:GameState {game_id: "401810220"})
MATCH (game)-[played:PLAYED]->(player:Player)
WHERE played.team = "home" AND played.minutes >= 25

WITH game, collect(player.name) AS key_players

MATCH (game)-[:FEATURED_TACTIC {team: "home"}]->(tactic:Tactic)
MATCH (tactic)-[req:REQUIRES_PLAYER]->(required:Player)

WITH game, tactic, key_players, collect(required.name) AS required_players

RETURN
  tactic.name,
  tactic.effectiveness,
  key_players,
  required_players,
  // 필수 선수가 모두 출전했는지 체크
  reduce(all_present = true, rp IN required_players |
    all_present AND rp IN key_players) AS tactic_fully_activated;

// ----------------------------------------------------------------------------
// 쿼리 3: 센군/아담스 조합 효과 (관계 기반)
// ----------------------------------------------------------------------------

MATCH (hou:Team {abbr: "HOU"})-[:USES_TACTIC]->(spacing:Tactic {name: "Inside Spacing"})
MATCH (spacing)-[:REQUIRES_PLAYER {role: "Floor Spacer"}]->(sengun:Player {name: "Sengun"})
MATCH (spacing)-[:REQUIRES_PLAYER {role: "Rim Protector"}]->(adams:Player {name: "Adams"})

MATCH (game:GameState)-[:PLAYED {team: "home"}]->(sengun)
MATCH (game)-[:PLAYED {team: "home"}]->(adams)
WHERE (game.home_team = "HOU" OR game.away_team = "HOU")

WITH game,
     CASE WHEN game.home_team = "HOU" THEN game.result.home_win ELSE NOT game.result.home_win END AS hou_win

RETURN
  count(*) AS games_with_combo,
  sum(CASE WHEN hou_win THEN 1 ELSE 0 END) * 1.0 / count(*) AS win_rate,
  avg(game.result.point_diff) AS avg_point_diff;

// ----------------------------------------------------------------------------
// 쿼리 4: Graph RAG - 유사 경기 찾기 (벡터 검색)
// ----------------------------------------------------------------------------

// 입력: 특정 게임의 임베딩
WITH $query_embedding AS query_vec

CALL db.index.vector.queryNodes('game_state_embedding', 10, query_vec)
YIELD node AS similar_game, score

MATCH (similar_game)-[:FEATURED_TACTIC]->(tactic:Tactic)
MATCH (similar_game)-[:OFFICIATED_BY]->(referee:Referee)

RETURN
  similar_game.game_id,
  similar_game.date,
  similar_game.home_team + ' vs ' + similar_game.away_team AS matchup,
  similar_game.result.home_win AS result,
  collect(tactic.name) AS tactics_used,
  collect(referee.name) AS referees,
  score AS similarity_score
ORDER BY score DESC
LIMIT 5;

// ============================================================================
// 데이터 입력 예시
// ============================================================================

// 팀 생성
CREATE (okc:Team {
  abbr: "OKC",
  name: "Oklahoma City Thunder",
  conference: "West",
  division: "Northwest",
  current_win_rate: 0.73,
  current_form_index: 0.82
});

// 전술 생성
CREATE (gapDef:Tactic {
  name: "Gap Defense",
  origin_team: "OKC",
  category: "defense",
  description: "드라이브 레인에 디펜더를 배치해 페인트 진입 차단",
  effectiveness: 0.78,
  sample_size: 50,
  statistical_signature: {
    opponent_paint_points_max: 40.0,
    steals_per_game_min: 10.0
  }
});

// 관계 생성
MATCH (okc:Team {abbr: "OKC"})
MATCH (gapDef:Tactic {name: "Gap Defense"})
CREATE (okc)-[:USES_TACTIC {
  start_date: date("2024-10-22"),
  frequency: 0.85,
  success_rate: 0.73
}]->(gapDef);

// 게임 생성 (라인업 포함)
CREATE (game:GameState {
  game_id: "401810220",
  date: date("2024-12-16"),
  season: "2024-25",
  home_team: "MIN",
  away_team: "PHX",
  home_rest_days: 1,
  away_rest_days: 2,
  home_injuries: ["Mike Conley - Day-To-Day"],
  away_injuries: ["Kevin Durant - Out"],
  referees: ["Scott Foster", "Tony Brothers"],
  result: {
    home_win: true,
    home_points: 118,
    away_points: 110,
    point_diff: 8
  },
  context_score: {
    rest_advantage: -1,
    injury_impact: 0.6,
    referee_bias: 0.2,
    tactic_favorability: 0.5
  }
});

// 라인업 추가 (피드백 4 적용!)
MATCH (game:GameState {game_id: "401810220"})
MATCH (ant:Player {name: "Anthony Edwards"})
CREATE (game)-[:STARTED {team: "home", position: "SG"}]->(ant);

MATCH (game:GameState {game_id: "401810220"})
MATCH (ant:Player {name: "Anthony Edwards"})
CREATE (game)-[:PLAYED {team: "home", minutes: 36, points: 28, plus_minus: 12}]->(ant);

// ============================================================================
// 마이그레이션 체크리스트
// ============================================================================

/*
✅ Phase 1: 기본 노드 생성
  - Teams (30개)
  - Players (450명 주요 선수)
  - Referees (70명)

✅ Phase 2: 게임 상태 마이그레이션
  - GameState (927개: 2024 485 + 2025 442)
  - STARTED/PLAYED 관계 (라인업)
  - OFFICIATED_BY 관계

✅ Phase 3: 전술 시드 데이터
  - 핵심 전술 10개 수작업 입력
  - USES_TACTIC 관계
  - REQUIRES_PLAYER 관계

✅ Phase 4: 전술 상성
  - COUNTERS 관계 (AI 분석 + 수작업)
  - 초기 20개 상성만 입력

✅ Phase 5: 벡터 임베딩
  - GameState.embedding 생성
  - Claude/GPT-4로 맥락 임베딩

✅ Phase 6: Graph Viewer 테스트
  - Neo4j Browser 커스터마이징
  - 핵심 쿼리 5개 테스트
*/

// ============================================================================
// 끝
// ============================================================================
// "설명용 필드"와 "계산용 필드"를 분리해라 - 반영 완료
// MatchupHistory는 관계로 - 반영 완료
// team_abbr 제거 - 반영 완료
// absence_penalty로 명확화 - 반영 완료
// lineups를 관계로 - 반영 완료
// Vector index는 GameState만 - 반영 완료
// ContextSnapshot은 옵션 - 반영 완료
// ============================================================================
