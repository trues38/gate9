/*
유사 경기 검색 쿼리
내일 경기와 유사한 과거 경기를 찾아서 분석 컨텍스트 제공
*/

-- ============================================================================
-- Query 1: 같은 매치업 과거 전적
-- ============================================================================
-- 사용법: {home_team}, {away_team} 파라미터 입력
-- 예: home_team = "OKC", away_team = "DEN"

MATCH (game:GameState)
WHERE game.home_team = $home_team AND game.away_team = $away_team
RETURN
  game.date AS 날짜,
  game.season AS 시즌,
  game.home_score AS 홈득점,
  game.away_score AS 원정득점,
  CASE WHEN game.home_win THEN 'W' ELSE 'L' END AS 결과,
  game.home_score - game.away_score AS 득점차,
  game.home_rest_days AS 홈휴식,
  game.away_rest_days AS 원정휴식
ORDER BY game.date DESC
LIMIT 10;


-- ============================================================================
-- Query 2: 휴식일 패턴이 유사한 경기 (같은 팀)
-- ============================================================================
-- 사용법: {home_team}, {away_team}, {home_rest}, {away_rest} 파라미터
-- 예: home_team = "OKC", away_team = "DEN", home_rest = 2, away_rest = 1

MATCH (game:GameState)
WHERE game.home_team = $home_team
  AND game.home_rest_days = $home_rest
  AND game.away_rest_days = $away_rest
RETURN
  game.date AS 날짜,
  game.away_team AS 상대팀,
  game.home_score AS 홈득점,
  game.away_score AS 원정득점,
  CASE WHEN game.home_win THEN 'W' ELSE 'L' END AS 결과,
  game.home_fg_pct AS 슈팅성공률,
  game.home_three_pt_pct AS 3점성공률
ORDER BY game.date DESC
LIMIT 5;


-- ============================================================================
-- Query 3: 심판 패턴 분석
-- ============================================================================
-- 사용법: {referee_name} 파라미터
-- 예: referee_name = "Scott Foster"

MATCH (ref:Referee {name: $referee_name})<-[:OFFICIATED_BY]-(game:GameState)
WITH ref,
     count(game) AS 총경기수,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS 홈승수,
     avg(game.home_score + game.away_score) AS 평균총득점,
     avg(game.home_score - game.away_score) AS 평균득점차
RETURN
  ref.name AS 심판,
  총경기수,
  round(홈승수 * 100.0 / 총경기수, 1) AS 홈승률,
  round(평균총득점, 1) AS 평균총득점,
  round(abs(평균득점차), 1) AS 평균득점차;


-- ============================================================================
-- Query 4: 특정 팀의 최근 폼 (최근 10경기)
-- ============================================================================
-- 사용법: {team} 파라미터
-- 예: team = "OKC"

MATCH (game:GameState)
WHERE game.home_team = $team OR game.away_team = $team
WITH game,
     CASE
       WHEN game.home_team = $team THEN game.home_win
       ELSE NOT game.home_win
     END AS win,
     CASE
       WHEN game.home_team = $team THEN game.home_score - game.away_score
       ELSE game.away_score - game.home_score
     END AS point_diff
ORDER BY game.date DESC
LIMIT 10
RETURN
  game.date AS 날짜,
  CASE WHEN game.home_team = $team THEN 'vs ' + game.away_team ELSE '@ ' + game.home_team END AS 상대,
  CASE WHEN win THEN 'W' ELSE 'L' END AS 결과,
  point_diff AS 득점차
ORDER BY game.date DESC;


-- ============================================================================
-- Query 5: 매치업 종합 통계
-- ============================================================================
-- 사용법: {home_team}, {away_team} 파라미터

MATCH (game:GameState)
WHERE game.home_team = $home_team AND game.away_team = $away_team
WITH
  count(game) AS 총경기수,
  sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS 홈승수,
  avg(game.home_score) AS 홈평균득점,
  avg(game.away_score) AS 원정평균득점,
  avg(game.home_score - game.away_score) AS 평균득점차,
  max(game.home_score - game.away_score) AS 최대득점차,
  min(game.home_score - game.away_score) AS 최소득점차
RETURN
  총경기수,
  홈승수,
  총경기수 - 홈승수 AS 원정승수,
  round(홈승수 * 100.0 / 총경기수, 1) AS 홈승률,
  round(홈평균득점, 1) AS 홈평균득점,
  round(원정평균득점, 1) AS 원정평균득점,
  round(평균득점차, 1) AS 평균득점차,
  최대득점차 AS 최대홈승차,
  최소득점차 AS 최대원정승차;


-- ============================================================================
-- Query 6: 홈/원정 별도 전적
-- ============================================================================
-- 사용법: {team} 파라미터

MATCH (home_games:GameState {home_team: $team})
WITH
  count(home_games) AS 홈경기수,
  sum(CASE WHEN home_games.home_win THEN 1 ELSE 0 END) AS 홈승수,
  avg(home_games.home_score) AS 홈평균득점
MATCH (away_games:GameState {away_team: $team})
WITH
  홈경기수, 홈승수, 홈평균득점,
  count(away_games) AS 원정경기수,
  sum(CASE WHEN NOT away_games.home_win THEN 1 ELSE 0 END) AS 원정승수,
  avg(away_games.away_score) AS 원정평균득점
RETURN
  홈경기수,
  홈승수,
  round(홈승수 * 100.0 / 홈경기수, 1) AS 홈승률,
  round(홈평균득점, 1) AS 홈평균득점,
  원정경기수,
  원정승수,
  round(원정승수 * 100.0 / 원정경기수, 1) AS 원정승률,
  round(원정평균득점, 1) AS 원정평균득점;


-- ============================================================================
-- Query 7: 휴식일별 승률 (특정 팀)
-- ============================================================================
-- 사용법: {team} 파라미터

MATCH (game:GameState)
WHERE game.home_team = $team
WITH game.home_rest_days AS 휴식일,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS 승수,
     count(game) AS 경기수
WHERE 경기수 >= 2
RETURN
  휴식일,
  경기수,
  승수,
  round(승수 * 100.0 / 경기수, 1) AS 승률
ORDER BY 휴식일

UNION ALL

MATCH (game:GameState)
WHERE game.away_team = $team
WITH game.away_rest_days AS 휴식일,
     sum(CASE WHEN NOT game.home_win THEN 1 ELSE 0 END) AS 승수,
     count(game) AS 경기수
WHERE 경기수 >= 2
RETURN
  휴식일,
  경기수,
  승수,
  round(승수 * 100.0 / 경기수, 1) AS 승률
ORDER BY 휴식일;


-- ============================================================================
-- Query 8: 선수별 평균 성적 (특정 팀 소속 경기)
-- ============================================================================
-- 사용법: {team} 파라미터

MATCH (game:GameState)-[played:PLAYED]->(player:Player)
WHERE played.team_abbr = $team AND played.minutes >= 15
WITH player,
     count(game) AS 경기수,
     avg(played.points) AS 평균득점,
     avg(played.rebounds) AS 평균리바운드,
     avg(played.assists) AS 평균어시스트,
     avg(played.plus_minus) AS 평균PM
WHERE 경기수 >= 3
RETURN
  player.name AS 선수,
  경기수,
  round(평균득점, 1) AS 평균득점,
  round(평균리바운드, 1) AS 평균리바운드,
  round(평균어시스트, 1) AS 평균어시스트,
  round(평균PM, 1) AS 평균PM
ORDER BY 평균득점 DESC
LIMIT 15;


-- ============================================================================
-- Query 9: 가장 유사한 경기 찾기 (복합 조건)
-- ============================================================================
-- 사용법: {home_team}, {away_team}, {home_rest}, {away_rest} 파라미터
-- 유사도 점수를 계산해서 가장 비슷한 경기 반환

MATCH (game:GameState)
WHERE game.home_team = $home_team AND game.away_team = $away_team
WITH game,
     abs(game.home_rest_days - $home_rest) AS rest_diff_home,
     abs(game.away_rest_days - $away_rest) AS rest_diff_away
WITH game,
     (5 - rest_diff_home - rest_diff_away) AS 유사도점수
WHERE 유사도점수 > 0
RETURN
  game.date AS 날짜,
  game.season AS 시즌,
  game.home_score AS 홈득점,
  game.away_score AS 원정득점,
  CASE WHEN game.home_win THEN 'W' ELSE 'L' END AS 결과,
  game.home_rest_days AS 홈휴식,
  game.away_rest_days AS 원정휴식,
  유사도점수
ORDER BY 유사도점수 DESC, game.date DESC
LIMIT 5;


-- ============================================================================
-- Query 10: 경기장 홈 어드밴티지 분석
-- ============================================================================
-- 사용법: {team} 파라미터 (홈 팀)

MATCH (venue:Venue)<-[:HOSTED_AT]-(game:GameState {home_team: $team})
WITH venue,
     count(game) AS 경기수,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS 승수,
     avg(game.home_score - game.away_score) AS 평균득점차
WHERE 경기수 >= 3
RETURN
  venue.name AS 경기장,
  venue.city AS 도시,
  경기수,
  승수,
  round(승수 * 100.0 / 경기수, 1) AS 승률,
  round(평균득점차, 1) AS 평균득점차
ORDER BY 승률 DESC;
