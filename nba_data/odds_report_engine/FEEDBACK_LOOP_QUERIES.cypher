// ============================================================
// NBA GraphRAG Feedback Loop - Cypher Queries
// ============================================================
// 경기 종료 후 자동 실행되는 쿼리들
// ============================================================


// ============================================================
// STEP 1: BoxScore 수집 및 연결
// ============================================================

// 경기 종료 후 BoxScore 생성
MERGE (g:Game {game_id: $game_id})
CREATE (b:BoxScore {
  game_id: $game_id,
  created_at: datetime(),

  // 실제 결과
  home_score: $home_score,
  away_score: $away_score,
  margin: $margin,

  // Spread 결과
  spread_line: $spread_line,
  spread_covered: $spread_covered,

  // 통계
  home_injuries_impact: $home_injuries_impact,
  away_injuries_impact: $away_injuries_impact,
  pace: $pace
})
CREATE (g)-[:RESULTED_IN {
  completed_at: datetime()
}]->(b)
RETURN b;


// ============================================================
// STEP 2: Event 검증 (일괄 처리)
// ============================================================

// 2-1. Injury Impact Event 검증
MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})-[:EXPECTED_FOR]->(g:Game)
MATCH (g)-[:RESULTED_IN]->(b:BoxScore)
WITH e, b,
     e.prediction.expected_impact AS expected,
     b.home_injuries_impact AS actual,
     abs(b.home_injuries_impact - e.prediction.expected_impact) AS error
CREATE (e)-[:VALIDATED {
  success: CASE WHEN error < 5.0 THEN true ELSE false END,
  impact_score: 1.0 - (error / 20.0),  // 0~1 점수
  actual_vs_expected: actual + " vs " + expected,
  error_margin: error,
  validated_at: datetime()
}]->(b)
RETURN e.event_id, error,
       CASE WHEN error < 5.0 THEN "SUCCESS" ELSE "FAILED" END AS result;


// 2-2. Market Signal Event 검증
MATCH (e:Event {game_id: $game_id, event_type: 'MARKET_SIGNAL'})-[:EXPECTED_FOR]->(g:Game)
MATCH (g)-[:RESULTED_IN]->(b:BoxScore)
WITH e, b,
     e.prediction.expected_spread_cover AS predicted_cover,
     b.spread_covered AS actual_cover
CREATE (e)-[:VALIDATED {
  success: CASE WHEN predicted_cover = actual_cover THEN true ELSE false END,
  impact_score: CASE WHEN predicted_cover = actual_cover THEN 1.0 ELSE 0.0 END,
  validated_at: datetime()
}]->(b)
RETURN e.event_id, predicted_cover, actual_cover;


// 2-3. AI Council Prediction 검증
MATCH (c:CouncilPrediction {game_id: $game_id})-[:PREDICTED_FOR]->(g:Game)
MATCH (g)-[:RESULTED_IN]->(b:BoxScore)
WITH c, b,
     c.recommendation AS pred,
     b.spread_covered AS actual
SET c.was_correct = CASE
  WHEN pred = 'BET' AND actual = 'AWAY' THEN true
  WHEN pred = 'PASS' AND actual = 'HOME' THEN true
  ELSE false
END,
c.actual_outcome = actual
CREATE (c)-[:VALIDATED {
  was_correct: c.was_correct,
  validated_at: datetime()
}]->(b)
RETURN c.consensus_score, c.was_correct;


// ============================================================
// STEP 3: State 업데이트 (핵심!)
// ============================================================

// 3-1. Team Regime Confidence 업데이트
// "Event가 성공하면 Regime Confidence 상승"
MATCH (e:Event {game_id: $game_id})-[v:VALIDATED]->(b:BoxScore)
MATCH (g:Game {game_id: $game_id})
MATCH (ts:TeamState {team_id: g.home_team})
WITH ts,
     count(e) AS total_events,
     sum(CASE WHEN v.success = true THEN 1 ELSE 0 END) AS successful_events,
     toFloat(sum(CASE WHEN v.success = true THEN 1 ELSE 0 END)) / count(e) AS success_rate
SET ts.regime_success_rate =
      (COALESCE(ts.regime_success_rate, 0.5) * 0.9) + (success_rate * 0.1),  // EMA
    ts.regime_confidence =
      CASE
        WHEN success_rate > 0.7 THEN COALESCE(ts.regime_confidence, 0.5) + 0.05
        WHEN success_rate < 0.3 THEN COALESCE(ts.regime_confidence, 0.5) - 0.05
        ELSE ts.regime_confidence
      END,
    ts.total_events_validated = COALESCE(ts.total_events_validated, 0) + total_events,
    ts.successful_predictions = COALESCE(ts.successful_predictions, 0) + successful_events,
    ts.updated_at = datetime()
CREATE (b)-[:UPDATED_STATE {
  update_type: 'REGIME_CONFIDENCE',
  delta: success_rate - 0.5,
  reason: total_events + " events validated",
  updated_at: datetime()
}]->(ts)
RETURN ts.team_id, ts.regime_confidence, ts.regime_success_rate;


// 3-2. Injury Resilience 업데이트
// "부상자 있었는데 이겼으면 Resilience UP"
MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})-[v:VALIDATED]->(b:BoxScore)
MATCH (g:Game {game_id: $game_id})
MATCH (ts:TeamState {team_id: g.home_team})
WITH ts, b, v,
     b.margin AS actual_margin,
     v.impact_score AS accuracy
SET ts.injury_impact_history =
      [accuracy] + COALESCE(ts.injury_impact_history, [])[0..2],  // 최근 3경기만
    ts.injury_resilience =
      CASE
        WHEN actual_margin > 0 AND e.prediction.expected_impact < -5.0 THEN "HIGH"  // 부상 예측했는데 이김
        WHEN actual_margin < -10 AND e.prediction.expected_impact < -5.0 THEN "LOW"  // 부상 예측대로 큰 패배
        ELSE "MEDIUM"
      END,
    ts.updated_at = datetime()
CREATE (b)-[:UPDATED_STATE {
  update_type: 'INJURY_RESILIENCE',
  delta: actual_margin,
  reason: "Injury impact: " + e.prediction.expected_impact,
  updated_at: datetime()
}]->(ts)
RETURN ts.team_id, ts.injury_resilience, ts.injury_impact_history;


// 3-3. Market Trust 업데이트
// "시장이 틀렸으면 Market Trust 감소"
MATCH (e:Event {game_id: $game_id, event_type: 'MARKET_SIGNAL'})-[v:VALIDATED]->(b:BoxScore)
MATCH (g:Game {game_id: $game_id})
MATCH (ts:TeamState {team_id: g.home_team})
WITH ts, v,
     toFloat(sum(CASE WHEN v.success = true THEN 1 ELSE 0 END)) / count(e) AS market_accuracy
SET ts.market_accuracy =
      (COALESCE(ts.market_accuracy, 0.5) * 0.85) + (market_accuracy * 0.15),  // EMA
    ts.market_trust =
      CASE
        WHEN ts.market_accuracy > 0.65 THEN "HIGH"
        WHEN ts.market_accuracy < 0.45 THEN "LOW"
        ELSE "MEDIUM"
      END,
    ts.updated_at = datetime()
CREATE (b)-[:UPDATED_STATE {
  update_type: 'MARKET_TRUST',
  delta: market_accuracy - 0.5,
  updated_at: datetime()
}]->(ts)
RETURN ts.team_id, ts.market_trust, ts.market_accuracy;


// 3-4. Player Impact 업데이트
// "선수가 결장했을 때 팀이 얼마나 버텼는지 학습"
MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})-[:VALIDATED]->(b:BoxScore)
MATCH (ps:PlayerState {player_id: $injured_player_id})
WITH ps, b, e,
     b.margin AS actual_margin,
     e.prediction.expected_impact AS expected_impact
SET ps.team_impact_when_out =
      (COALESCE(ps.team_impact_when_out, 0.5) * 0.8) +
      ((abs(actual_margin) / 20.0) * 0.2),  // 0~1 정규화
    ps.games_missed_last_30d = COALESCE(ps.games_missed_last_30d, 0) + 1,
    ps.updated_at = datetime()
RETURN ps.player_id, ps.team_impact_when_out;


// 3-5. AI Council 성공률 추적 (메타 학습)
MATCH (c:CouncilPrediction)-[v:VALIDATED]->(b:BoxScore)
WHERE b.created_at > datetime() - duration({days: 30})
WITH
  count(c) AS total,
  sum(CASE WHEN v.was_correct = true THEN 1 ELSE 0 END) AS correct,
  toFloat(sum(CASE WHEN v.was_correct = true THEN 1 ELSE 0 END)) / count(c) AS accuracy
MERGE (meta:SystemMetrics {id: 'ai_council'})
SET meta.total_predictions = total,
    meta.correct_predictions = correct,
    meta.accuracy_30d = accuracy,
    meta.updated_at = datetime()
RETURN meta.accuracy_30d;


// ============================================================
// STEP 4: Event Archive (선택사항)
// ============================================================

// 검증된 Event를 Archive로 이동 (성능 최적화)
MATCH (e:Event)-[:VALIDATED]->(b:BoxScore)
WHERE b.created_at < datetime() - duration({days: 7})
SET e:ArchivedEvent
REMOVE e:Event
RETURN count(e) AS archived_count;


// ============================================================
// 📊 State 조회 쿼리 (다음 경기 분석용)
// ============================================================

// Query 1: 다음 경기 분석용 Team State 조회
MATCH (ts:TeamState {team_id: $team_id})
RETURN {
  team_id: ts.team_id,

  // Regime
  current_regime: ts.current_regime,
  regime_confidence: ts.regime_confidence,
  regime_success_rate: ts.regime_success_rate,

  // Injury Resilience
  injury_resilience: ts.injury_resilience,
  injury_impact_history: ts.injury_impact_history,

  // Market Trust
  market_trust: ts.market_trust,
  market_accuracy: ts.market_accuracy,

  // Performance
  recent_form: ts.recent_form,
  avg_margin: ts.avg_margin,

  // Metadata
  total_events_validated: ts.total_events_validated,
  successful_predictions: ts.successful_predictions,
  updated_at: ts.updated_at
} AS team_state;


// Query 2: H2H State (과거 대결 누적 학습 결과)
MATCH (ts1:TeamState {team_id: $team1}),
      (ts2:TeamState {team_id: $team2})
OPTIONAL MATCH (g:Game)-[:RESULTED_IN]->(b:BoxScore)
WHERE (g.home_team = $team1 AND g.away_team = $team2)
   OR (g.home_team = $team2 AND g.away_team = $team1)
WITH ts1, ts2,
     collect({
       date: g.date,
       margin: b.margin,
       spread_covered: b.spread_covered
     })[0..5] AS recent_h2h
RETURN {
  team1_state: {
    regime: ts1.current_regime,
    confidence: ts1.regime_confidence,
    resilience: ts1.injury_resilience
  },
  team2_state: {
    regime: ts2.current_regime,
    confidence: ts2.regime_confidence,
    resilience: ts2.injury_resilience
  },
  h2h_history: recent_h2h
} AS matchup_state;


// Query 3: Player State 조회 (부상자 영향도 예측용)
MATCH (ps:PlayerState {player_id: $player_id})
RETURN {
  player_id: ps.player_id,
  team_id: ps.team_id,

  // Performance
  ppg: ps.ppg,
  recent_games: ps.recent_games,

  // Injury Pattern (학습된 값)
  injury_prone: ps.injury_prone,
  injury_recovery_rate: ps.injury_recovery_rate,

  // Team Impact (학습된 영향도)
  team_impact_when_out: ps.team_impact_when_out,
  replacement_quality: ps.replacement_quality
} AS player_state;


// ============================================================
// 📈 분석 쿼리 (시스템 성능 체크)
// ============================================================

// Analysis 1: Regime 예측 성공률
MATCH (ts:TeamState)
WHERE ts.total_events_validated > 10
RETURN ts.team_id,
       ts.current_regime,
       ts.regime_success_rate,
       ts.total_events_validated
ORDER BY ts.regime_success_rate DESC
LIMIT 10;


// Analysis 2: AI Council 개선 추적
MATCH (c:CouncilPrediction)-[:VALIDATED {was_correct: true}]->(b:BoxScore)
WHERE b.created_at > datetime() - duration({days: 30})
WITH date(b.created_at) AS day, count(c) AS correct
MATCH (c2:CouncilPrediction)-[:VALIDATED]->(b2:BoxScore)
WHERE b2.created_at > datetime() - duration({days: 30})
  AND date(b2.created_at) = day
WITH day, correct, count(c2) AS total
RETURN day, toFloat(correct) / total AS daily_accuracy
ORDER BY day DESC;


// Analysis 3: Injury Resilience 패턴 발견
MATCH (ts:TeamState)
WHERE ts.injury_resilience = 'HIGH'
  AND size(ts.injury_impact_history) >= 3
RETURN ts.team_id,
       ts.injury_resilience,
       ts.injury_impact_history,
       "이 팀은 부상에도 잘 버티는 팀" AS insight;


// ============================================================
// 🎯 핵심 원칙 정리
// ============================================================
//
// 1. Event는 검증 후 Archive (또는 삭제)
// 2. State는 계속 업데이트 (EMA 방식으로 smooth)
// 3. BoxScore는 정답지 역할
// 4. 다음 경기는 State만 조회 (Event 조회 안 함)
// 5. 시스템이 스스로 학습 (Meta Metrics 추적)
//
// ============================================================
