#!/usr/bin/env python3
"""
Economic State Ontology
========================
기존 레짐 분류 전면 폐기.
시장을 비가역적 상태 그래프로 재설계.

이건 예측기가 아니다.
이건 상태 기계 기록기다.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List
from enum import Enum


class ActivationLevel(Enum):
    """상태 활성화 수준"""
    DORMANT = 0      # 잠복
    LOW = 1          # 약함
    ELEVATED = 2     # 상승
    HIGH = 3         # 높음
    PEAK = 4         # 최고조
    FRACTURING = 5   # 붕괴 중


@dataclass
class StateNode:
    """
    State 노드 정의
    - 자산 이름은 State가 될 수 없음 (GOLD, SP500 ❌)
    - 현상/관계/구조만 State가 됨
    """
    id: str
    activation_drivers: List[str]      # 정량/정성 혼합 드라이버
    observable_signals: List[str]      # 가격 아님, 관계/현상
    interaction_states: Set[str]       # 동시 활성화 가능
    blocked_states: Set[str]           # 동시 활성화 불가
    description: str = ""              # 내부 참조용 (출력 안 함)


# ============================================
# STATE ONTOLOGY (25개 State 노드)
# ============================================

STATE_ONTOLOGY: Dict[str, StateNode] = {

    # ========== LIQUIDITY STATES ==========

    "LIQUIDITY_STRESS": StateNode(
        id="LIQUIDITY_STRESS",
        activation_drivers=[
            "LIQUIDITY_DEMAND > LIQUIDITY_SUPPLY_CAPACITY",
            "MARGIN_ABSORPTION_FAILING",
            "SAFE_ASSET_FORCED_LIQUIDATION",
        ],
        observable_signals=[
            "safe_assets_sold_despite_fear",
            "correlation_approaching_one",
            "bid_ask_spreads_widening",
        ],
        interaction_states={"DELEVERAGING_PRESSURE", "DOLLAR_LIQUIDITY_TIGHTENING"},
        blocked_states={"LIQUIDITY_ABUNDANCE", "RISK_APPETITE_EXPANSION"},
    ),

    "LIQUIDITY_ABUNDANCE": StateNode(
        id="LIQUIDITY_ABUNDANCE",
        activation_drivers=[
            "CENTRAL_BANK_BALANCE_SHEET_EXPANDING",
            "CREDIT_SPREADS_COMPRESSING",
            "FUNDING_MARKETS_STABLE",
        ],
        observable_signals=[
            "carry_trades_profitable",
            "vol_selling_dominant",
            "all_assets_lifted",
        ],
        interaction_states={"RISK_APPETITE_EXPANSION", "LEVERAGE_ACCUMULATION"},
        blocked_states={"LIQUIDITY_STRESS", "DELEVERAGING_PRESSURE"},
    ),

    "DOLLAR_LIQUIDITY_TIGHTENING": StateNode(
        id="DOLLAR_LIQUIDITY_TIGHTENING",
        activation_drivers=[
            "OFFSHORE_DOLLAR_SHORTAGE",
            "CROSS_CURRENCY_BASIS_WIDENING",
            "EM_RESERVE_DRAWDOWN",
        ],
        observable_signals=[
            "em_forced_selling",
            "dollar_strength_despite_fundamentals",
            "global_asset_repatriation",
        ],
        interaction_states={"LIQUIDITY_STRESS", "CAPITAL_FLIGHT"},
        blocked_states={"LIQUIDITY_ABUNDANCE"},
    ),

    # ========== LEVERAGE STATES ==========

    "DELEVERAGING_PRESSURE": StateNode(
        id="DELEVERAGING_PRESSURE",
        activation_drivers=[
            "MARGIN_CALLS_CASCADING",
            "POSITION_UNWINDING_FORCED",
            "COLLATERAL_VALUE_DECLINING",
        ],
        observable_signals=[
            "correlation_spike_across_assets",
            "vol_of_vol_elevated",
            "redemption_pressure_visible",
        ],
        interaction_states={"LIQUIDITY_STRESS", "MARKET_STRUCTURE_STRAIN"},
        blocked_states={"LEVERAGE_ACCUMULATION"},
    ),

    "LEVERAGE_ACCUMULATION": StateNode(
        id="LEVERAGE_ACCUMULATION",
        activation_drivers=[
            "VOL_SUPPRESSION_PERSISTENT",
            "FUNDING_COST_LOW",
            "CARRY_RETURNS_ATTRACTIVE",
        ],
        observable_signals=[
            "short_vol_crowding",
            "margin_debt_rising",
            "risk_parity_expanding",
        ],
        interaction_states={"LIQUIDITY_ABUNDANCE", "RISK_APPETITE_EXPANSION"},
        blocked_states={"DELEVERAGING_PRESSURE"},
    ),

    # ========== POLICY STATES ==========

    "POLICY_CREDIBILITY_DECAY": StateNode(
        id="POLICY_CREDIBILITY_DECAY",
        activation_drivers=[
            "POLICY_SIGNAL_IGNORED_BY_MARKET",
            "FORWARD_GUIDANCE_FAILURE",
            "INFLATION_EXPECTATION_UNANCHORED",
        ],
        observable_signals=[
            "long_bonds_selling_despite_dovish",
            "term_premium_rising",
            "real_rates_disconnected",
        ],
        interaction_states={"FISCAL_DOMINANCE", "INFLATION_REGIME_SHIFT"},
        blocked_states={"POLICY_CREDIBILITY_STRONG"},
    ),

    "POLICY_CREDIBILITY_STRONG": StateNode(
        id="POLICY_CREDIBILITY_STRONG",
        activation_drivers=[
            "FORWARD_GUIDANCE_EFFECTIVE",
            "INFLATION_EXPECTATIONS_ANCHORED",
            "MARKET_FOLLOWS_FED",
        ],
        observable_signals=[
            "curve_responds_to_guidance",
            "vol_compressed_post_fomc",
            "risk_assets_rally_on_dovish",
        ],
        interaction_states={"RISK_APPETITE_EXPANSION"},
        blocked_states={"POLICY_CREDIBILITY_DECAY", "FISCAL_DOMINANCE"},
    ),

    "FISCAL_DOMINANCE": StateNode(
        id="FISCAL_DOMINANCE",
        activation_drivers=[
            "DEFICIT_MONETIZATION_IMPLICIT",
            "TREASURY_SUPPLY_OVERWHELMING",
            "CENTRAL_BANK_INDEPENDENCE_QUESTIONED",
        ],
        observable_signals=[
            "long_rates_rising_despite_cuts",
            "currency_weakening_with_easing",
            "gold_and_btc_correlating",
        ],
        interaction_states={"POLICY_CREDIBILITY_DECAY", "INFLATION_REGIME_SHIFT"},
        blocked_states={"POLICY_CREDIBILITY_STRONG"},
    ),

    "CENTRAL_BANK_REACTION_IMMINENT": StateNode(
        id="CENTRAL_BANK_REACTION_IMMINENT",
        activation_drivers=[
            "FINANCIAL_CONDITIONS_TIGHTENING_FAST",
            "CREDIT_STRESS_VISIBLE",
            "MARKET_FORCING_POLICY",
        ],
        observable_signals=[
            "fed_speakers_dovish_pivot",
            "emergency_liquidity_discussed",
            "vol_spike_triggering_response",
        ],
        interaction_states={"LIQUIDITY_STRESS", "DELEVERAGING_PRESSURE"},
        blocked_states={"POLICY_CREDIBILITY_STRONG"},
    ),

    # ========== RISK STATES ==========

    "RISK_APPETITE_EXPANSION": StateNode(
        id="RISK_APPETITE_EXPANSION",
        activation_drivers=[
            "VOL_COMPRESSION_SUSTAINED",
            "CREDIT_SPREADS_TIGHT",
            "EQUITY_RISK_PREMIUM_LOW",
        ],
        observable_signals=[
            "junk_outperforming_quality",
            "speculative_flows_dominant",
            "put_call_ratio_low",
        ],
        interaction_states={"LIQUIDITY_ABUNDANCE", "LEVERAGE_ACCUMULATION"},
        blocked_states={"RISK_APPETITE_SUPPRESSED", "LIQUIDITY_STRESS"},
    ),

    "RISK_APPETITE_SUPPRESSED": StateNode(
        id="RISK_APPETITE_SUPPRESSED",
        activation_drivers=[
            "UNCERTAINTY_ELEVATED",
            "HEDGING_DEMAND_RISING",
            "DEFENSIVE_ROTATION_VISIBLE",
        ],
        observable_signals=[
            "quality_outperforming_junk",
            "safe_haven_bid_persistent",
            "equity_vol_premium_high",
        ],
        interaction_states={"LIQUIDITY_STRESS", "GEOPOLITICAL_PREMIUM"},
        blocked_states={"RISK_APPETITE_EXPANSION"},
    ),

    "RISK_PREMIUM_REPRICING": StateNode(
        id="RISK_PREMIUM_REPRICING",
        activation_drivers=[
            "VALUATION_MULTIPLE_COMPRESSION",
            "DISCOUNT_RATE_ADJUSTMENT",
            "GROWTH_EXPECTATION_REVISION",
        ],
        observable_signals=[
            "pe_ratios_falling",
            "duration_sensitive_selling",
            "growth_to_value_rotation",
        ],
        interaction_states={"POLICY_CREDIBILITY_DECAY", "INFLATION_REGIME_SHIFT"},
        blocked_states={"RISK_APPETITE_EXPANSION"},
    ),

    # ========== SAFE HAVEN STATES ==========

    "SAFE_HAVEN_CONGESTION": StateNode(
        id="SAFE_HAVEN_CONGESTION",
        activation_drivers=[
            "FLIGHT_TO_SAFETY_CROWDED",
            "SAFE_ASSET_SUPPLY_CONSTRAINED",
            "NEGATIVE_YIELD_TOLERANCE_TESTED",
        ],
        observable_signals=[
            "safe_assets_overvalued",
            "safety_premium_extreme",
            "traditional_hedges_failing",
        ],
        interaction_states={"RISK_APPETITE_SUPPRESSED", "NARRATIVE_FRAGMENTATION"},
        blocked_states={"RISK_APPETITE_EXPANSION"},
    ),

    "SAFE_HAVEN_DIVERGENCE": StateNode(
        id="SAFE_HAVEN_DIVERGENCE",
        activation_drivers=[
            "TRADITIONAL_VS_ALTERNATIVE_SPLIT",
            "GOLD_BTC_CORRELATION_BREAKDOWN",
            "BOND_EQUITY_CORRELATION_UNSTABLE",
        ],
        observable_signals=[
            "gold_and_bonds_decoupling",
            "btc_failing_as_hedge",
            "correlation_structure_unstable",
        ],
        interaction_states={"NARRATIVE_FRAGMENTATION", "LIQUIDITY_STRESS"},
        blocked_states=set(),
    ),

    # ========== INFLATION STATES ==========

    "INFLATION_REGIME_SHIFT": StateNode(
        id="INFLATION_REGIME_SHIFT",
        activation_drivers=[
            "INFLATION_EXPECTATION_RISING",
            "WAGE_PRICE_SPIRAL_RISK",
            "SUPPLY_SIDE_CONSTRAINTS_PERSISTENT",
        ],
        observable_signals=[
            "tips_breakeven_rising",
            "nominal_vs_real_diverging",
            "commodity_currencies_strong",
        ],
        interaction_states={"POLICY_CREDIBILITY_DECAY", "FISCAL_DOMINANCE"},
        blocked_states={"DISINFLATION_REGIME"},
    ),

    "DISINFLATION_REGIME": StateNode(
        id="DISINFLATION_REGIME",
        activation_drivers=[
            "DEMAND_DESTRUCTION_VISIBLE",
            "SUPPLY_CHAIN_NORMALIZING",
            "CREDIT_CONTRACTION_DEFLATIONARY",
        ],
        observable_signals=[
            "breakevens_falling",
            "commodity_weakness",
            "duration_outperforming",
        ],
        interaction_states={"CENTRAL_BANK_REACTION_IMMINENT"},
        blocked_states={"INFLATION_REGIME_SHIFT"},
    ),

    # ========== MARKET STRUCTURE STATES ==========

    "MARKET_STRUCTURE_STRAIN": StateNode(
        id="MARKET_STRUCTURE_STRAIN",
        activation_drivers=[
            "MARKET_MAKING_CAPACITY_REDUCED",
            "DEALER_BALANCE_SHEET_CONSTRAINED",
            "LIQUIDITY_PROVISION_WITHDRAWN",
        ],
        observable_signals=[
            "flash_crash_risk_elevated",
            "depth_of_book_thin",
            "execution_quality_deteriorating",
        ],
        interaction_states={"LIQUIDITY_STRESS", "DELEVERAGING_PRESSURE"},
        blocked_states={"LIQUIDITY_ABUNDANCE"},
    ),

    "CORRELATION_REGIME_BREAK": StateNode(
        id="CORRELATION_REGIME_BREAK",
        activation_drivers=[
            "HISTORICAL_CORRELATION_FAILING",
            "FACTOR_MODEL_BREAKDOWN",
            "REGIME_SWITCH_INDICATORS",
        ],
        observable_signals=[
            "cross_asset_relationships_unstable",
            "quant_strategies_underperforming",
            "dispersion_extreme",
        ],
        interaction_states={"NARRATIVE_FRAGMENTATION", "MARKET_STRUCTURE_STRAIN"},
        blocked_states=set(),
    ),

    # ========== NARRATIVE STATES ==========

    "NARRATIVE_FRAGMENTATION": StateNode(
        id="NARRATIVE_FRAGMENTATION",
        activation_drivers=[
            "CONFLICTING_SIGNALS_DOMINANT",
            "MARKET_CONSENSUS_ABSENT",
            "POSITIONING_CONFUSED",
        ],
        observable_signals=[
            "contradictory_asset_moves",
            "survey_divergence_extreme",
            "low_conviction_trading",
        ],
        interaction_states={"SAFE_HAVEN_DIVERGENCE", "CORRELATION_REGIME_BREAK"},
        blocked_states={"NARRATIVE_CONSENSUS"},
    ),

    "NARRATIVE_CONSENSUS": StateNode(
        id="NARRATIVE_CONSENSUS",
        activation_drivers=[
            "DOMINANT_THEME_CLEAR",
            "POSITIONING_ALIGNED",
            "CROWDED_TRADES_VISIBLE",
        ],
        observable_signals=[
            "one_way_flows",
            "consensus_trades_extended",
            "contrarian_opportunity_building",
        ],
        interaction_states={"RISK_APPETITE_EXPANSION", "LEVERAGE_ACCUMULATION"},
        blocked_states={"NARRATIVE_FRAGMENTATION"},
    ),

    # ========== EXTERNAL STATES ==========

    "GEOPOLITICAL_PREMIUM": StateNode(
        id="GEOPOLITICAL_PREMIUM",
        activation_drivers=[
            "CONFLICT_RISK_ELEVATED",
            "SUPPLY_DISRUPTION_THREAT",
            "SANCTION_REGIME_SHIFTING",
        ],
        observable_signals=[
            "energy_risk_premium_high",
            "defense_sector_outperforming",
            "safe_haven_bid_geopolitical",
        ],
        interaction_states={"RISK_APPETITE_SUPPRESSED", "INFLATION_REGIME_SHIFT"},
        blocked_states=set(),
    ),

    "CAPITAL_FLIGHT": StateNode(
        id="CAPITAL_FLIGHT",
        activation_drivers=[
            "INSTITUTIONAL_TRUST_ERODING",
            "CURRENCY_CRISIS_RISK",
            "CAPITAL_CONTROLS_ANTICIPATED",
        ],
        observable_signals=[
            "em_outflows_accelerating",
            "reserve_currency_premium",
            "offshore_accumulation",
        ],
        interaction_states={"DOLLAR_LIQUIDITY_TIGHTENING", "GEOPOLITICAL_PREMIUM"},
        blocked_states={"LIQUIDITY_ABUNDANCE"},
    ),

    # ========== TRANSITION STATES ==========

    "REGIME_TRANSITION_ZONE": StateNode(
        id="REGIME_TRANSITION_ZONE",
        activation_drivers=[
            "MULTIPLE_STATES_ACTIVE",
            "TRANSITION_SIGNALS_MIXED",
            "STABILITY_INDICATORS_WEAK",
        ],
        observable_signals=[
            "vol_of_vol_elevated",
            "trend_following_whipsawed",
            "mean_reversion_failing",
        ],
        interaction_states=set(),  # 모든 State와 공존 가능
        blocked_states=set(),
    ),

    "MARKET_FREEZE": StateNode(
        id="MARKET_FREEZE",
        activation_drivers=[
            "LIQUIDITY_PROVISION_ZERO",
            "PRICE_DISCOVERY_FAILING",
            "CIRCUIT_BREAKERS_TRIGGERED",
        ],
        observable_signals=[
            "trading_halts",
            "no_bid_markets",
            "emergency_intervention_required",
        ],
        interaction_states={"LIQUIDITY_STRESS", "MARKET_STRUCTURE_STRAIN"},
        blocked_states={"LIQUIDITY_ABUNDANCE", "RISK_APPETITE_EXPANSION"},
    ),
}


def get_state_ontology() -> Dict[str, StateNode]:
    """State Ontology 반환"""
    return STATE_ONTOLOGY


def get_state_ids() -> List[str]:
    """모든 State ID 반환"""
    return list(STATE_ONTOLOGY.keys())


def get_interaction_graph() -> Dict[str, Set[str]]:
    """State 간 상호작용 그래프 반환"""
    return {
        state_id: state.interaction_states
        for state_id, state in STATE_ONTOLOGY.items()
    }


def get_blocking_graph() -> Dict[str, Set[str]]:
    """State 간 차단 그래프 반환"""
    return {
        state_id: state.blocked_states
        for state_id, state in STATE_ONTOLOGY.items()
    }
