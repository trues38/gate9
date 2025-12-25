/*
Graph Viewer MVP - 핵심 Cypher 쿼리 5개
==========================================
목표: "전술 → 카운터 → 결과" 3단 흐름 시각화

Made with ❤️ by State Graph Engine
*/

-- ============================================================================
-- Query 1: 전술 상성 네트워크 (핵심!)
-- ============================================================================
-- 목적: Gap Defense를 카운터하는 전술은?

MATCH (tactic:Tactic {name: "Gap Defense"})
MATCH (counter:Tactic)-[c:COUNTERS]->(tactic)
RETURN
  tactic.name AS 원본전술,
  counter.name AS 카운터전술,
  c.win_rate AS 승률,
  c.avg_point_diff AS 평균점수차,
  c.sample_size AS 샘플수
ORDER BY c.win_rate DESC;

-- 예상 결과:
-- Gap Defense <- No-Pick Roll Play (0.72 승률, +8.5 점수차)


-- ============================================================================
-- Query 2: 전술 상성 전체 네트워크 (시각화용)
-- ============================================================================
-- 목적: Neo4j Browser에서 네트워크 그래프 보기

MATCH (t1:Tactic)-[c:COUNTERS]->(t2:Tactic)
WHERE c.sample_size >= 5  // 샘플 5개 이상만
RETURN t1, c, t2
ORDER BY c.win_rate DESC
LIMIT 20;

-- 시각화: 노드 크기 = effectiveness, 선 굵기 = win_rate


-- ============================================================================
-- Query 3: 팀별 전술 사용 현황
-- ============================================================================
-- 목적: OKC가 어떤 전술을 주로 사용하나?

MATCH (team:Team {abbr: "OKC"})
MATCH (game:GameState)
WHERE game.home_team = "OKC" OR game.away_team = "OKC"

MATCH (game)-[:FEATURED_TACTIC]->(tactic:Tactic)

WITH team, tactic, count(game) AS usage_count,
     sum(CASE
       WHEN (game.home_team = "OKC" AND game.result.home_win)
         OR (game.away_team = "OKC" AND NOT game.result.home_win)
       THEN 1 ELSE 0
     END) AS wins

RETURN
  team.abbr AS 팀,
  tactic.name AS 전술,
  usage_count AS 사용횟수,
  wins * 1.0 / usage_count AS 승률,
  tactic.category AS 카테고리
ORDER BY usage_count DESC
LIMIT 10;

-- 예상 결과:
-- OKC | Gap Defense | 45경기 | 0.73 승률


-- ============================================================================
-- Query 4: 특정 경기 컨텍스트 전체 (상세 분석)
-- ============================================================================
-- 목적: 401810220 경기의 모든 맥락 보기

MATCH (game:GameState {game_id: "401810220"})

// 홈팀
MATCH (home:Team {abbr: game.home_team})

// 어웨이팀
MATCH (away:Team {abbr: game.away_team})

// 심판
OPTIONAL MATCH (game)-[:OFFICIATED_BY]->(ref:Referee)

// 선발 라인업
OPTIONAL MATCH (game)-[started:STARTED]->(player:Player)

// 주요 선수 (20분 이상)
OPTIONAL MATCH (game)-[played:PLAYED]->(key_player:Player)
WHERE played.minutes >= 20

// 사용된 전술
OPTIONAL MATCH (game)-[:FEATURED_TACTIC]->(tactic:Tactic)

RETURN
  game.game_id AS 경기ID,
  game.date AS 날짜,
  home.abbr + " vs " + away.abbr AS 매치업,

  // 경기 결과
  game.result.home_score + "-" + game.result.away_score AS 스코어,
  CASE WHEN game.result.home_win THEN home.abbr ELSE away.abbr END AS 승자,

  // 컨텍스트
  game.context.home_rest_days AS 홈휴식,
  game.context.away_rest_days AS 어웨이휴식,
  collect(DISTINCT ref.name) AS 심판진,

  // 선발
  collect(DISTINCT {player: player.name, team: started.team, position: started.position}) AS 선발라인업,

  // 주요 선수
  collect(DISTINCT {
    player: key_player.name,
    team: played.team,
    minutes: played.minutes,
    points: played.points,
    plus_minus: played.plus_minus
  }) AS 주요선수,

  // 전술
  collect(DISTINCT tactic.name) AS 사용전술;


-- ============================================================================
-- Query 5: 유사 경기 검색 (Vector Search)
-- ============================================================================
-- 목적: "401810220과 비슷한 경기는?"

// 타겟 경기
MATCH (target:GameState {game_id: "401810220"})

// Vector 유사도 (Neo4j GDS)
CALL gds.similarity.cosine.stream({
  nodeProjection: 'GameState',
  relationshipProjection: '*',
  sourceNode: target,
  topK: 10
})
YIELD node1, node2, similarity

// 유사 경기 정보
MATCH (similar:GameState)
WHERE id(similar) = id(node2)

// 그 경기의 전술
OPTIONAL MATCH (similar)-[:FEATURED_TACTIC]->(tactic:Tactic)

RETURN
  target.game_id AS 원본경기,
  similar.game_id AS 유사경기,
  similar.date AS 날짜,
  similar.home_team + " vs " + similar.away_team AS 매치업,
  similarity AS 유사도,
  collect(tactic.name) AS 사용전술
ORDER BY similarity DESC
LIMIT 10;


-- ============================================================================
-- Query 6: 선수-전술 의존도 (심화)
-- ============================================================================
-- 목적: Gap Defense는 어떤 선수에 의존하나?

MATCH (tactic:Tactic {name: "Gap Defense"})
MATCH (tactic)-[req:REQUIRES_PLAYER]->(player:Player)

RETURN
  tactic.name AS 전술,
  player.name AS 필수선수,
  req.role AS 역할,
  req.absence_penalty AS 결석시페널티,
  req.min_minutes AS 최소출전시간
ORDER BY req.absence_penalty DESC;

-- 예상 결과:
-- Gap Defense | Lu Dort | Perimeter Defender | 0.9 | 25분


-- ============================================================================
-- Query 7: 전술 효과 by 심판
-- ============================================================================
-- 목적: Scott Foster 때 Gap Defense 효과는?

MATCH (ref:Referee {name: "Scott Foster"})
MATCH (game:GameState)-[:OFFICIATED_BY]->(ref)
MATCH (game)-[:FEATURED_TACTIC]->(tactic:Tactic {name: "Gap Defense"})

WITH tactic, ref, count(game) AS games_count,
     sum(CASE WHEN game.result.home_win THEN 1 ELSE 0 END) AS home_wins

RETURN
  ref.name AS 심판,
  tactic.name AS 전술,
  games_count AS 경기수,
  home_wins * 1.0 / games_count AS 승률,

  // 비교: 전체 평균
  tactic.effectiveness AS 전체평균승률
ORDER BY games_count DESC;


-- ============================================================================
-- Query 8: 매치업 히스토리 (팀간 전적)
-- ============================================================================
-- 목적: OKC vs MIA 과거 전적 + 전술 패턴

MATCH (team1:Team {abbr: "OKC"})
MATCH (team2:Team {abbr: "MIA"})
MATCH (team1)-[matchup:MATCHUP]->(team2)

// 최근 경기들
MATCH (game:GameState)
WHERE (game.home_team = "OKC" AND game.away_team = "MIA")
   OR (game.home_team = "MIA" AND game.away_team = "OKC")

// 각 경기의 전술
OPTIONAL MATCH (game)-[:FEATURED_TACTIC]->(tactic:Tactic)

RETURN
  team1.abbr + " vs " + team2.abbr AS 매치업,
  matchup.wins AS OKC승,
  matchup.losses AS OKC패,
  matchup.avg_point_diff AS 평균점수차,
  matchup.dominant_tactic AS 주요전술,

  // 최근 경기 리스트
  collect({
    date: game.date,
    score: game.result.home_score + "-" + game.result.away_score,
    winner: CASE WHEN game.result.home_win THEN game.home_team ELSE game.away_team END,
    tactics: collect(tactic.name)
  }) AS 최근경기들
ORDER BY matchup.wins DESC;


-- ============================================================================
-- Query 9: 레짐 트렌드 (시간별 변화)
-- ============================================================================
-- 목적: 12월에 어떤 전술이 뜨고 있나?

MATCH (trend:LeagueTrend)
WHERE trend.month >= "2024-12" AND trend.month <= "2025-01"

MATCH (trend)-[:TRENDING_TACTIC]->(tactic:Tactic)

RETURN
  trend.month AS 월,
  tactic.name AS 전술,
  trend.avg_pace AS 평균템포,
  trend.avg_three_point_rate AS 평균3점비율,
  trend.dominant_style AS 주류스타일
ORDER BY trend.month DESC, tactic.name;


-- ============================================================================
-- Query 10: 전술 진화 경로
-- ============================================================================
-- 목적: Gap Defense가 어떻게 진화했나?

MATCH (current:Tactic {name: "Gap Defense"})

// 이 전술을 카운터하는 전술들
MATCH (counter1:Tactic)-[:COUNTERS]->(current)

// 그 카운터를 다시 카운터하는 전술들
OPTIONAL MATCH (counter2:Tactic)-[:COUNTERS]->(counter1)

RETURN
  current.name AS 원본,
  collect(DISTINCT counter1.name) AS 1차카운터,
  collect(DISTINCT counter2.name) AS 2차카운터
LIMIT 1;

-- 예상 결과:
-- Gap Defense → [No-Pick Roll, Pace & Space] → [Inside Spacing, 20-30min Rotation]


-- ============================================================================
-- 성능 최적화 팁
-- ============================================================================

/*
1. Index 필수:
   CREATE INDEX game_date FOR (g:GameState) ON (g.date);
   CREATE INDEX tactic_name FOR (t:Tactic) ON (t.name);
   CREATE INDEX team_abbr FOR (t:Team) ON (t.abbr);

2. Vector Search 설정:
   CALL db.index.vector.createNodeIndex(
     'gameStateVector',
     'GameState',
     'embedding',
     1536,
     'cosine'
   );

3. 쿼리 프로파일링:
   PROFILE <your query>
   → 병목 찾기

4. 메모리 설정 (docker run):
   -e NEO4J_server_memory_heap_initial__size=2G
   -e NEO4J_server_memory_heap_max__size=4G
*/


-- ============================================================================
-- 다음 단계
-- ============================================================================

/*
1. Neo4j Docker 설치
2. Constraints & Indexes 생성
3. 샘플 데이터 임포트 (10개 경기)
4. 위 쿼리들 실행 테스트
5. React + D3.js 시각화 (선택)
*/
