// ============================================
// Economic Regime State Graph Schema
// ============================================
// 이건 리포트가 아니다. 상태 공간이다.
// ============================================

// ============================================
// 1. CORE NODE TYPES (문장 없음, 구조만)
// ============================================

// MacroFactor: 거시 요인 (측정값)
// - 인플레이션, 성장, 고용, 유동성 등
CREATE CONSTRAINT macro_factor_id IF NOT EXISTS
FOR (m:MacroFactor) REQUIRE m.id IS UNIQUE;

// PolicySignal: 정책 신호 (Fed, ECB, BOJ 등)
// - hawkish, dovish, pause, pivot
CREATE CONSTRAINT policy_signal_id IF NOT EXISTS
FOR (p:PolicySignal) REQUIRE p.id IS UNIQUE;

// MarketStress: 시장 스트레스 상태
// - liquidity_stress, volatility_spike, correlation_breakdown
CREATE CONSTRAINT market_stress_id IF NOT EXISTS
FOR (s:MarketStress) REQUIRE s.id IS UNIQUE;

// AssetReaction: 자산 반응 패턴
// - gold_up, btc_down, vix_spike, dxy_surge
CREATE CONSTRAINT asset_reaction_id IF NOT EXISTS
FOR (a:AssetReaction) REQUIRE a.id IS UNIQUE;

// LiquidityState: 유동성 상태
// - abundant, tightening, crisis
CREATE CONSTRAINT liquidity_state_id IF NOT EXISTS
FOR (l:LiquidityState) REQUIRE l.id IS UNIQUE;

// RegimeState: 레짐 상태 노드 (라벨 아님!)
// - 상태: ACTIVE, STRENGTHENING, WEAKENING, DORMANT, TRANSITIONING
CREATE CONSTRAINT regime_state_id IF NOT EXISTS
FOR (r:RegimeState) REQUIRE r.id IS UNIQUE;

// ShockEvent: 충격 이벤트 노드
// - fed_speak, geopolitical, data_surprise, correlation_break
CREATE CONSTRAINT shock_event_id IF NOT EXISTS
FOR (e:ShockEvent) REQUIRE e.id IS UNIQUE;


// ============================================
// 2. REGIME STATE DEFINITIONS (문장 없이)
// ============================================

// Core Regime States - 상태 ID만, 설명 없음
MERGE (r1:RegimeState {id: 'LIQUIDITY_STRESS'})
SET r1.state = 'DORMANT', r1.activation = 0.0;

MERGE (r2:RegimeState {id: 'STAGFLATION_PRESSURE'})
SET r2.state = 'DORMANT', r2.activation = 0.0;

MERGE (r3:RegimeState {id: 'POLICY_CREDIBILITY_LOSS'})
SET r3.state = 'DORMANT', r3.activation = 0.0;

MERGE (r4:RegimeState {id: 'RISK_ON_EUPHORIA'})
SET r4.state = 'DORMANT', r4.activation = 0.0;

MERGE (r5:RegimeState {id: 'DELEVERAGING'})
SET r5.state = 'DORMANT', r5.activation = 0.0;

MERGE (r6:RegimeState {id: 'DOLLAR_DEFLATION'})
SET r6.state = 'DORMANT', r6.activation = 0.0;

MERGE (r7:RegimeState {id: 'NARRATIVE_COLLAPSE'})
SET r7.state = 'DORMANT', r7.activation = 0.0;

MERGE (r8:RegimeState {id: 'SAFE_ASSET_DIVERGENCE'})
SET r8.state = 'DORMANT', r8.activation = 0.0;

MERGE (r9:RegimeState {id: 'FED_PUT_ACTIVE'})
SET r9.state = 'DORMANT', r9.activation = 0.0;

MERGE (r10:RegimeState {id: 'MIXED_TRANSITION'})
SET r10.state = 'DORMANT', r10.activation = 0.0;


// ============================================
// 3. CORE RELATIONSHIPS
// ============================================

// MacroFactor → MarketStress (증폭)
// (MacroFactor)-[:AMPLIFIES {weight}]->(MarketStress)

// PolicySignal → MarketStress (억제 또는 실패)
// (PolicySignal)-[:SUPPRESSES {effectiveness}]->(MarketStress)
// (PolicySignal)-[:FAILS_TO_SUPPRESS {reason}]->(MarketStress)

// ShockEvent → RegimeState (왜곡)
// (ShockEvent)-[:DISTORTS {magnitude, direction}]->(RegimeState)

// AssetReaction → RegimeState (확인 또는 모순)
// (AssetReaction)-[:CONFIRMS {confidence}]->(RegimeState)
// (AssetReaction)-[:CONTRADICTS {confidence}]->(RegimeState)

// RegimeState → RegimeState (전이)
// (RegimeState)-[:TRANSITIONS_TO {probability, trigger}]->(RegimeState)


// ============================================
// 4. REGIME TRANSITION GRAPH (핵심!)
// ============================================

// LIQUIDITY_STRESS 전이 경로
MATCH (r1:RegimeState {id: 'LIQUIDITY_STRESS'})
MATCH (r2:RegimeState {id: 'DELEVERAGING'})
MATCH (r3:RegimeState {id: 'DOLLAR_DEFLATION'})
MATCH (r4:RegimeState {id: 'FED_PUT_ACTIVE'})
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.4, trigger: 'vix_above_25'}]->(r2)
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.3, trigger: 'dxy_surge_2pct'}]->(r3)
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.3, trigger: 'fed_emergency'}]->(r4);

// STAGFLATION_PRESSURE 전이 경로
MATCH (r1:RegimeState {id: 'STAGFLATION_PRESSURE'})
MATCH (r2:RegimeState {id: 'POLICY_CREDIBILITY_LOSS'})
MATCH (r3:RegimeState {id: 'MIXED_TRANSITION'})
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.5, trigger: 'cpi_above_3pct'}]->(r2)
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.5, trigger: 'growth_stabilizes'}]->(r3);

// POLICY_CREDIBILITY_LOSS 전이 경로
MATCH (r1:RegimeState {id: 'POLICY_CREDIBILITY_LOSS'})
MATCH (r2:RegimeState {id: 'DELEVERAGING'})
MATCH (r3:RegimeState {id: 'NARRATIVE_COLLAPSE'})
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.6, trigger: 'bond_selloff'}]->(r2)
MERGE (r1)-[:TRANSITIONS_TO {probability: 0.4, trigger: 'btc_gold_diverge'}]->(r3);


// ============================================
// 5. SHOCK → REGIME DISTORTION PATTERNS
// ============================================

// Fed Hawkish Shock → Multiple Regimes
// CREATE (e:ShockEvent {id: 'fed_hawkish_20251230', type: 'FED_SPEAK', magnitude: 0.7})
// MATCH (r1:RegimeState {id: 'LIQUIDITY_STRESS'})
// MATCH (r2:RegimeState {id: 'FED_PUT_ACTIVE'})
// MERGE (e)-[:DISTORTS {magnitude: +0.3, direction: 'strengthen'}]->(r1)
// MERGE (e)-[:DISTORTS {magnitude: -0.5, direction: 'weaken'}]->(r2)


// ============================================
// 6. ASSET REACTION → REGIME CONFIRMATION
// ============================================

// Gold ↓ + VIX ↑ = LIQUIDITY_STRESS 확인
// Gold ↑ + VIX ↓ = LIQUIDITY_STRESS 모순
// BTC ↓ + DXY ↓ = NARRATIVE_COLLAPSE 확인
// BTC ↑ + Gold ↑ = SAFE_ASSET_DIVERGENCE 확인


// ============================================
// 7. SUBGRAPH SIMILARITY QUERY (Twin 검색)
// ============================================

// 날짜 기반이 아닌, 구조적 유사성 검색
// MATCH path = (shock:ShockEvent)-[:DISTORTS]->(regime:RegimeState)
// WHERE regime.state = 'ACTIVE'
// WITH collect(regime.id) as active_regimes, collect(shock.type) as shock_types
// MATCH (historical_shock:ShockEvent)-[:DISTORTS]->(historical_regime:RegimeState)
// WHERE historical_regime.id IN active_regimes
// RETURN historical_shock, historical_regime,
//        size([r IN active_regimes WHERE historical_regime.id = r]) as similarity_score
// ORDER BY similarity_score DESC
// LIMIT 5;
