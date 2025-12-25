/*
Neo4j Schema - Clean Version
=============================
전술 제거, 검증 가능한 데이터만

원칙:
1. 실체가 명확한 것만 (팀, 선수, 심판, 경기장, 경기)
2. ESPN API에서 직접 추출 가능
3. 해석이나 추론 불필요

Made with ❤️ by State Graph Engine
*/

-- ============================================================================
-- Constraints (데이터 무결성)
-- ============================================================================

// 팀 ID 유일성
CREATE CONSTRAINT team_abbr IF NOT EXISTS
FOR (t:Team) REQUIRE t.abbr IS UNIQUE;

// 선수 이름 유일성 (간단화)
CREATE CONSTRAINT player_name IF NOT EXISTS
FOR (p:Player) REQUIRE p.name IS UNIQUE;

// 심판 이름 유일성
CREATE CONSTRAINT referee_name IF NOT EXISTS
FOR (r:Referee) REQUIRE r.name IS UNIQUE;

// 경기장 ID 유일성
CREATE CONSTRAINT venue_id IF NOT EXISTS
FOR (v:Venue) REQUIRE v.id IS UNIQUE;

// 경기 ID 유일성
CREATE CONSTRAINT game_id IF NOT EXISTS
FOR (g:GameState) REQUIRE g.game_id IS UNIQUE;


-- ============================================================================
-- Indexes (쿼리 성능)
-- ============================================================================

// 날짜별 경기 검색
CREATE INDEX game_date IF NOT EXISTS
FOR (g:GameState) ON (g.date);

// 시즌별 경기 검색
CREATE INDEX game_season IF NOT EXISTS
FOR (g:GameState) ON (g.season);

// 팀별 검색
CREATE INDEX game_home_team IF NOT EXISTS
FOR (g:GameState) ON (g.home_team);

CREATE INDEX game_away_team IF NOT EXISTS
FOR (g:GameState) ON (g.away_team);


-- ============================================================================
-- 노드 정의 (5개만)
-- ============================================================================

// ----------------------------------------------------------------------------
// 1. Team (팀)
// ----------------------------------------------------------------------------
CREATE (team:Team {
  abbr: STRING,              // "OKC", "MIA", "GS"
  name: STRING,              // "Oklahoma City Thunder"

  // 기본 정보
  conference: STRING,        // "West", "East"
  division: STRING,          // "Northwest", "Southeast", etc.

  // 계산 가능 (나중에 집계)
  total_games: INTEGER,      // 전체 경기 수
  total_wins: INTEGER,       // 전체 승수
  avg_points_scored: FLOAT,  // 평균 득점
  avg_points_allowed: FLOAT  // 평균 실점
});

// ----------------------------------------------------------------------------
// 2. Player (선수)
// ----------------------------------------------------------------------------
CREATE (player:Player {
  name: STRING,              // "Shai Gilgeous-Alexander"

  // 기본 정보
  position: STRING,          // "G", "F", "C"
  jersey_number: STRING,     // "2"

  // 계산 가능 (나중에 집계)
  total_games: INTEGER,      // 출전 경기 수
  avg_points: FLOAT,         // 평균 득점
  avg_minutes: FLOAT,        // 평균 출전시간
  avg_plus_minus: FLOAT      // 평균 +/-
});

// ----------------------------------------------------------------------------
// 3. Referee (심판)
// ----------------------------------------------------------------------------
CREATE (referee:Referee {
  name: STRING,              // "Scott Foster"

  // 계산 가능 (나중에 집계)
  total_games: INTEGER,      // 배정된 경기 수
  home_win_rate: FLOAT,      // 홈 팀 승률
  avg_total_fouls: FLOAT,    // 평균 파울 콜 수
  avg_total_points: FLOAT    // 평균 총 득점 (템포 지표)
});

// ----------------------------------------------------------------------------
// 4. Venue (경기장)
// ----------------------------------------------------------------------------
CREATE (venue:Venue {
  id: STRING,                // ESPN venue ID
  name: STRING,              // "Paycom Center"

  // 위치
  city: STRING,              // "Oklahoma City"
  state: STRING,             // "Oklahoma"

  // 계산 가능
  total_games: INTEGER,      // 개최 경기 수
  avg_total_points: FLOAT,   // 평균 총 득점
  home_win_rate: FLOAT       // 홈 승률
});

// ----------------------------------------------------------------------------
// 5. GameState (경기 상태 - 핵심!)
// ----------------------------------------------------------------------------
CREATE (game:GameState {
  // 식별자
  game_id: STRING,           // "401704627"
  date: DATE,                // 2024-10-22
  season: STRING,            // "2024-25"

  // 팀
  home_team: STRING,         // "BOS"
  away_team: STRING,         // "NY"

  // 경기 결과 (검증 가능)
  home_score: INTEGER,       // 132
  away_score: INTEGER,       // 109
  home_win: BOOLEAN,         // true

  // 컨텍스트 (검증 가능)
  home_rest_days: INTEGER,   // 3
  away_rest_days: INTEGER,   // 3
  is_conference_game: BOOLEAN,
  is_division_game: BOOLEAN,

  // 팀 통계 (검증 가능 - boxscore에서 추출)
  home_fg_pct: FLOAT,        // 0.551
  away_fg_pct: FLOAT,        // 0.550
  home_three_pt_pct: FLOAT,  // 0.367
  away_three_pt_pct: FLOAT,  // 0.367
  home_ft_pct: FLOAT,        // Field Throw %
  away_ft_pct: FLOAT,

  home_rebounds: INTEGER,
  away_rebounds: INTEGER,
  home_assists: INTEGER,
  away_assists: INTEGER,
  home_turnovers: INTEGER,
  away_turnovers: INTEGER,
  home_steals: INTEGER,
  away_steals: INTEGER,
  home_blocks: INTEGER,
  away_blocks: INTEGER,

  // 부가 정보
  attendance: INTEGER,       // 관중 수
  duration_minutes: INTEGER  // 경기 시간
});


-- ============================================================================
-- 관계 정의 (4개만)
-- ============================================================================

// ----------------------------------------------------------------------------
// 1. 출전 기록 (GameState → Player)
// ----------------------------------------------------------------------------
CREATE (game:GameState)-[:PLAYED {
  // 어느 팀으로 출전했는지
  team: STRING,              // "home" or "away"
  team_abbr: STRING,         // "OKC"

  // 선발/후보
  starter: BOOLEAN,          // true if started

  // 출전 통계 (boxscore에서 추출)
  minutes: INTEGER,          // 출전시간
  points: INTEGER,           // 득점
  rebounds: INTEGER,         // 리바운드
  assists: INTEGER,          // 어시스트
  steals: INTEGER,
  blocks: INTEGER,
  turnovers: INTEGER,

  // 슈팅
  fg_made: INTEGER,          // Field Goals Made
  fg_attempted: INTEGER,
  three_pt_made: INTEGER,
  three_pt_attempted: INTEGER,
  ft_made: INTEGER,
  ft_attempted: INTEGER,

  // 효율성
  plus_minus: INTEGER,       // +/-
  fg_pct: FLOAT,
  three_pt_pct: FLOAT,
  ft_pct: FLOAT
}]->(player:Player);

// ----------------------------------------------------------------------------
// 2. 심판 배정 (GameState → Referee)
// ----------------------------------------------------------------------------
CREATE (game:GameState)-[:OFFICIATED_BY {
  position: STRING,          // "Referee", "Umpire #1", "Umpire #2"
  order: INTEGER             // 1, 2, 3
}]->(referee:Referee);

// ----------------------------------------------------------------------------
// 3. 경기장 (GameState → Venue)
// ----------------------------------------------------------------------------
CREATE (game:GameState)-[:HOSTED_AT]->(venue:Venue);

// ----------------------------------------------------------------------------
// 4. 팀간 매치업 (Team ↔ Team)
// ----------------------------------------------------------------------------
CREATE (team1:Team)-[:MATCHUP {
  season: STRING,            // "2024-25"

  // 전적 (집계)
  wins: INTEGER,             // team1이 이긴 횟수
  losses: INTEGER,           // team1이 진 횟수

  // 평균
  avg_point_diff: FLOAT,     // team1 기준 평균 득실차
  avg_home_point_diff: FLOAT,// 홈 경기 평균 득실차
  avg_away_point_diff: FLOAT,// 원정 경기 평균 득실차

  // 샘플
  total_games: INTEGER       // 총 대결 횟수
}]->(team2:Team);


-- ============================================================================
-- 샘플 데이터 (예시)
-- ============================================================================

// Team
CREATE (okc:Team {
  abbr: "OKC",
  name: "Oklahoma City Thunder",
  conference: "West",
  division: "Northwest"
});

CREATE (mia:Team {
  abbr: "MIA",
  name: "Miami Heat",
  conference: "East",
  division: "Southeast"
});

// Player
CREATE (sga:Player {
  name: "Shai Gilgeous-Alexander",
  position: "G",
  jersey_number: "2"
});

CREATE (bam:Player {
  name: "Bam Adebayo",
  position: "C",
  jersey_number: "13"
});

// Referee
CREATE (foster:Referee {
  name: "Scott Foster"
});

// Venue
CREATE (paycom:Venue {
  id: "3654",
  name: "Paycom Center",
  city: "Oklahoma City",
  state: "Oklahoma"
});

// GameState
CREATE (game1:GameState {
  game_id: "401810220",
  date: date("2024-11-05"),
  season: "2024-25",

  home_team: "OKC",
  away_team: "MIA",

  home_score: 104,
  away_score: 97,
  home_win: true,

  home_rest_days: 1,
  away_rest_days: 2,

  home_fg_pct: 0.485,
  away_fg_pct: 0.450
});

// Relationships
CREATE (game1)-[:PLAYED {
  team: "home",
  team_abbr: "OKC",
  starter: true,
  minutes: 35,
  points: 29,
  rebounds: 5,
  assists: 8,
  plus_minus: 12,
  fg_pct: 0.524
}]->(sga);

CREATE (game1)-[:PLAYED {
  team: "away",
  team_abbr: "MIA",
  starter: true,
  minutes: 34,
  points: 22,
  rebounds: 11,
  assists: 4,
  plus_minus: -8,
  fg_pct: 0.478
}]->(bam);

CREATE (game1)-[:OFFICIATED_BY {
  position: "Referee",
  order: 1
}]->(foster);

CREATE (game1)-[:HOSTED_AT]->(paycom);

CREATE (okc)-[:MATCHUP {
  season: "2024-25",
  wins: 1,
  losses: 0,
  avg_point_diff: 7.0,
  total_games: 1
}]->(mia);


-- ============================================================================
-- 유의미한 쿼리 예시
-- ============================================================================

// 1. 심판별 홈 승률
MATCH (ref:Referee)<-[:OFFICIATED_BY]-(game:GameState)
WITH ref,
     count(game) as total_games,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) as home_wins
WHERE total_games >= 10  // 최소 10경기
RETURN ref.name as 심판,
       total_games as 경기수,
       round(home_wins * 100.0 / total_games, 1) as 홈승률
ORDER BY 홈승률 DESC;

// 2. 휴식일별 승률 차이
MATCH (game:GameState)
WITH game.home_rest_days - game.away_rest_days as rest_advantage,
     CASE WHEN game.home_win THEN 1 ELSE 0 END as home_win
RETURN rest_advantage as 휴식일차,
       count(*) as 경기수,
       round(avg(home_win) * 100, 1) as 홈승률
ORDER BY 휴식일차;

// 3. 선수별 출전 통계
MATCH (player:Player)<-[played:PLAYED]-(game:GameState)
WHERE played.minutes >= 20  // 20분 이상 출전
WITH player,
     count(game) as games,
     avg(played.points) as avg_pts,
     avg(played.plus_minus) as avg_pm
WHERE games >= 5  // 최소 5경기
RETURN player.name as 선수,
       games as 경기수,
       round(avg_pts, 1) as 평균득점,
       round(avg_pm, 1) as 평균PM
ORDER BY avg_pts DESC
LIMIT 20;

// 4. 경기장별 총 득점 (템포 지표)
MATCH (venue:Venue)<-[:HOSTED_AT]-(game:GameState)
WITH venue,
     count(game) as games,
     avg(game.home_score + game.away_score) as avg_total
WHERE games >= 5
RETURN venue.name as 경기장,
       games as 경기수,
       round(avg_total, 1) as 평균총득점
ORDER BY avg_total DESC;

// 5. 팀간 매치업 분석
MATCH (t1:Team)-[m:MATCHUP]->(t2:Team)
WHERE m.total_games >= 2
RETURN t1.abbr + " vs " + t2.abbr as 매치업,
       m.wins + "-" + m.losses as 전적,
       round(m.avg_point_diff, 1) as 평균득실차
ORDER BY m.total_games DESC;

// 6. B2B (Back-to-Back) 효과
MATCH (game:GameState)
WHERE game.home_rest_days = 0  // 홈팀이 B2B
WITH count(game) as b2b_games,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) as b2b_wins
RETURN b2b_games as B2B경기수,
       round(b2b_wins * 100.0 / b2b_games, 1) as B2B승률;

// 7. 컨퍼런스 경기 vs 디비전 경기
MATCH (game:GameState)
RETURN game.is_conference_game as 컨퍼런스경기,
       count(*) as 경기수,
       round(avg(abs(game.home_score - game.away_score)), 1) as 평균점수차
ORDER BY 컨퍼런스경기;

// 8. 선수 조합 효과 (같이 출전했을 때)
MATCH (p1:Player)<-[played1:PLAYED]-(game:GameState)-[played2:PLAYED]->(p2:Player)
WHERE p1.name < p2.name  // 중복 방지
  AND played1.team = played2.team  // 같은 팀
  AND played1.minutes >= 20 AND played2.minutes >= 20
WITH p1, p2,
     count(game) as games,
     avg(played1.plus_minus + played2.plus_minus) / 2.0 as avg_combined_pm
WHERE games >= 3
RETURN p1.name + " + " + p2.name as 조합,
       games as 경기수,
       round(avg_combined_pm, 1) as 평균PM
ORDER BY avg_combined_pm DESC
LIMIT 10;

// 9. 심판별 평균 총 득점 (템포 영향)
MATCH (ref:Referee)<-[:OFFICIATED_BY]-(game:GameState)
WITH ref,
     count(game) as games,
     avg(game.home_score + game.away_score) as avg_total_points
WHERE games >= 10
RETURN ref.name as 심판,
       games as 경기수,
       round(avg_total_points, 1) as 평균총득점
ORDER BY avg_total_points DESC;

// 10. 원정 연속 경기 효과 (Road Trip)
MATCH (game1:GameState), (game2:GameState)
WHERE game1.away_team = game2.away_team
  AND game2.date = game1.date + duration({days: 1})
  AND game1.away_rest_days <= 1
WITH game2,
     count(*) as road_trip_indicator
WHERE road_trip_indicator > 0
RETURN count(game2) as 원정연속경기수,
       sum(CASE WHEN NOT game2.home_win THEN 1 ELSE 0 END) as 원정팀승수,
       round(sum(CASE WHEN NOT game2.home_win THEN 1 ELSE 0 END) * 100.0 / count(game2), 1) as 원정승률;


-- ============================================================================
-- 다음 단계
-- ============================================================================

/*
1. migrate_to_neo4j_clean.py 작성
   - 927게임 전체 임포트
   - boxscore에서 선수 통계 추출
   - gameInfo에서 심판, 경기장 추출

2. Neo4j 실행
   docker run -d --name neo4j-nba ...

3. 마이그레이션 실행
   python3 migrate_to_neo4j_clean.py

4. 쿼리 테스트
   위의 10개 쿼리 실행
*/
