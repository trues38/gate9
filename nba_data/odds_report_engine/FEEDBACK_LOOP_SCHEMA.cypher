// ============================================================
// NBA GraphRAG Feedback Loop Schema
// ============================================================
// 목표: Event는 버리고, State만 누적하여 자기 학습하는 시스템
// ============================================================

// ============================================================
// 1. 노드 정의
// ============================================================

// --- Team State (다음 경기에서 사용) ---
(:TeamState {
  team_id: "TOR",
  updated_at: datetime,

  // Regime (누적 학습)
  current_regime: "DECLINE",
  regime_confidence: 0.87,
  regime_games: 12,
  regime_success_rate: 0.73,  // Event 검증 결과 누적

  // Injury Resilience (학습된 부상 대응력)
  injury_resilience: "LOW",  // LOW/MEDIUM/HIGH
  injury_impact_history: [0.8, 0.9, 0.7],  // 최근 3경기 부상 영향도

  // Market Trust (시장 신뢰도)
  market_trust: "MEDIUM",
  market_accuracy: 0.62,  // 라인 움직임 정확도

  // Performance Metrics (누적 통계)
  recent_form: "3-7",
  avg_margin: -5.1,
  home_record: "8-12",
  away_record: "5-15",

  // Learning Metadata
  total_events_validated: 45,
  successful_predictions: 28
})

// --- Player State (다음 경기에서 사용) ---
(:PlayerState {
  player_id: "rj_barrett",
  team_id: "TOR",
  updated_at: datetime,

  // Performance
  ppg: 21.5,
  recent_games: [18, 24, 19],  // 최근 3경기 득점

  // Injury History (학습된 부상 패턴)
  injury_prone: true,
  injury_recovery_rate: 0.65,
  games_missed_last_30d: 8,

  // Impact on Team (학습된 영향도)
  team_impact_when_out: 0.82,  // 결장 시 팀 승률 감소폭
  replacement_quality: 0.45  // 백업 선수 대체 품질
})

// --- Game (경기 메타데이터) ---
(:Game {
  game_id: "401810212",
  date: date,
  home_team: "TOR",
  away_team: "GSW",
  season: "2024-25",
  status: "COMPLETED"  // SCHEDULED, IN_PROGRESS, COMPLETED
})

// --- Event (경기 전 가설 - 일회용) ---
(:Event {
  event_id: "evt_001",
  game_id: "401810212",
  created_at: datetime,

  event_type: "INJURY_IMPACT",  // INJURY_IMPACT, MARKET_SIGNAL, LINEUP_CHANGE, etc.

  // 예측 내용
  prediction: {
    "expected_impact": -8.5,  // TOR 예상 점수 하락
    "confidence": 0.75,
    "reasoning": "RJ Barrett OUT (21.5ppg)"
  },

  // 검증 여부
  validated: false,
  validation_result: null
})

// --- BoxScore (경기 후 결과 - 정답지) ---
(:BoxScore {
  game_id: "401810212",
  created_at: datetime,

  // 실제 결과
  home_score: 102,
  away_score: 115,
  margin: -13,

  // Spread 결과
  spread_line: -4.5,
  spread_covered: "AWAY",

  // 주요 통계
  home_injuries_impact: -12.3,  // 실제 측정된 부상 영향
  away_injuries_impact: -3.1,

  pace: 98.5,
  home_fg_pct: 0.42,
  away_fg_pct: 0.51
})

// --- AI Council Prediction (5인 위원회 예측) ---
(:CouncilPrediction {
  game_id: "401810212",
  created_at: datetime,

  // 위원회 결과
  consensus_score: "3/5",
  recommendation: "BET",
  confidence: "MEDIUM",

  // 개별 AI 투표
  deepseek_vote: "BET",
  qwen_vote: "BET",
  grok_vote: "PASS",
  gemini_vote: "BET",
  gpt_vote: "PASS",

  // 검증 결과
  was_correct: null,  // BoxScore 후 채점
  actual_outcome: null
})


// ============================================================
// 2. 관계 정의
// ============================================================

// --- 경기 전: Event 생성 ---
(:Event)-[:EXPECTED_FOR {
  created_at: datetime,
  priority: "HIGH"  // Event 중요도
}]->(:Game)

// --- 경기 전: AI 예측 ---
(:CouncilPrediction)-[:PREDICTED_FOR {
  created_at: datetime
}]->(:Game)

// --- 경기 후: BoxScore 연결 ---
(:Game)-[:RESULTED_IN {
  completed_at: datetime
}]->(:BoxScore)

// --- 경기 후: Event 검증 ---
(:Event)-[:VALIDATED {
  success: true/false,
  impact_score: 0.82,  // 예측 정확도
  actual_vs_expected: -12.3 vs -8.5,
  validated_at: datetime
}]->(:BoxScore)

// --- 경기 후: AI 예측 검증 ---
(:CouncilPrediction)-[:VALIDATED {
  was_correct: true/false,
  margin_error: 2.5,
  validated_at: datetime
}]->(:BoxScore)

// --- 경기 후: State 업데이트 ---
(:BoxScore)-[:UPDATED_STATE {
  update_type: "REGIME_CONFIDENCE",
  delta: +0.05,  // 변화량
  reason: "3연속 예측 성공",
  updated_at: datetime
}]->(:TeamState)

// --- State와 Game 연결 (다음 경기 분석용) ---
(:TeamState)-[:APPLICABLE_TO {
  snapshot_at: datetime
}]->(:Game)


// ============================================================
// 3. 인덱스 (성능 최적화)
// ============================================================

CREATE INDEX team_state_id IF NOT EXISTS FOR (t:TeamState) ON (t.team_id);
CREATE INDEX game_id IF NOT EXISTS FOR (g:Game) ON (g.game_id);
CREATE INDEX event_game IF NOT EXISTS FOR (e:Event) ON (e.game_id);
CREATE INDEX player_state_id IF NOT EXISTS FOR (p:PlayerState) ON (p.player_id);

// ============================================================
// 4. 제약 조건
// ============================================================

CREATE CONSTRAINT unique_team_state IF NOT EXISTS
FOR (t:TeamState) REQUIRE t.team_id IS UNIQUE;

CREATE CONSTRAINT unique_game IF NOT EXISTS
FOR (g:Game) REQUIRE g.game_id IS UNIQUE;

CREATE CONSTRAINT unique_boxscore IF NOT EXISTS
FOR (b:BoxScore) REQUIRE b.game_id IS UNIQUE;


// ============================================================
// 📝 핵심 원칙
// ============================================================
//
// 1. Event는 VALIDATED 후 버린다 (또는 archive)
// 2. State만 계속 업데이트하며 누적한다
// 3. BoxScore는 채점기 역할 (Event와 AI 예측을 검증)
// 4. 다음 경기 분석 시 State만 조회한다
// 5. "오답 노트" = State 업데이트 로직
//
// ============================================================
