#!/usr/bin/env python3
"""
Economic State Machine Engine
==============================
기존 레짐 분류 전면 폐기.
시장을 비가역적 상태 그래프로 재설계.

금지사항:
- 단일 숫자 트리거 (VIX > 25 ❌)
- 예측, 전망, 추천
- 레짐 이름, 라벨링

이건 상태 기계 기록기다.
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum

from state_ontology import (
    STATE_ONTOLOGY,
    StateNode,
    ActivationLevel,
    get_state_ids,
    get_interaction_graph,
    get_blocking_graph,
)


# ============================================
# 1. STATE ACTIVATION LOGIC
# ============================================

@dataclass
class MarketObservation:
    """시장 관측값 (가격이 아닌 관계/현상)"""
    timestamp: str

    # 관계적 관측 (가격 아님!)
    safe_asset_liquidation: bool = False      # 안전자산이 공포 속에 매도됨
    correlation_converging: bool = False       # 상관관계 1로 수렴
    policy_signal_ignored: bool = False        # 정책 신호가 무시됨
    safe_haven_diverging: bool = False         # 안전자산 간 괴리
    vol_regime_shifting: bool = False          # 변동성 레짐 전환
    liquidity_absorption_failing: bool = False # 유동성 흡수 실패
    narrative_conflicting: bool = False        # 내러티브 충돌
    leverage_unwinding: bool = False           # 레버리지 청산
    flight_to_quality: bool = False            # 품질로의 도피
    risk_seeking_dominant: bool = False        # 위험 추구 지배적

    # 불균형 측정 (단일 숫자 아님!)
    liquidity_demand_vs_supply: float = 0.0    # >0: 수요 > 공급
    policy_credibility_delta: float = 0.0       # <0: 신뢰 하락
    risk_appetite_momentum: float = 0.0         # 위험 선호 모멘텀
    safe_haven_congestion_level: float = 0.0    # 안전자산 혼잡도
    correlation_instability: float = 0.0        # 상관관계 불안정성


@dataclass
class StateActivation:
    """State 활성화 상태"""
    state_id: str
    level: ActivationLevel
    drivers_active: List[str]
    confidence: float  # 0.0 ~ 1.0


# ============================================
# 2. OBSERVATION EXTRACTOR
# ============================================

class ObservationExtractor:
    """
    시장 데이터에서 관측값 추출
    가격 → 관계/현상으로 변환
    """

    def extract(self, econ_data: dict, date: str) -> MarketObservation:
        """경제 데이터에서 MarketObservation 추출"""

        mp = econ_data.get("market_prices", {})
        obs = MarketObservation(timestamp=date)

        # 개별 변화율 추출
        gold_chg = mp.get("Gold", {}).get("change_pct", 0)
        vix_chg = mp.get("VIX", {}).get("change_pct", 0)
        spy_chg = mp.get("S&P 500", {}).get("change_pct", 0)
        btc_chg = mp.get("Bitcoin", {}).get("change_pct", 0)
        tlt_chg = mp.get("20Y Treasury", {}).get("change_pct", 0)
        oil_chg = mp.get("Oil", {}).get("change_pct", 0)
        dxy_chg = mp.get("Dollar Index", {}).get("change_pct", 0)

        # ========== 관계적 관측 추출 ==========

        # 1. Safe Asset Liquidation: Gold↓ + VIX↑ = 공포 속 안전자산 매도
        if gold_chg < -1.5 and vix_chg > 2.0:
            obs.safe_asset_liquidation = True

        # 2. Correlation Converging: 모든 자산 동조
        changes = [gold_chg, spy_chg, btc_chg, tlt_chg, oil_chg]
        negative_count = sum(1 for c in changes if c < -0.5)
        if negative_count >= 4:
            obs.correlation_converging = True

        # 3. Policy Signal Ignored: 채권↓ + 주식↓ (동시 하락)
        if tlt_chg < -0.5 and spy_chg < -0.3:
            obs.policy_signal_ignored = True

        # 4. Safe Haven Diverging: Gold vs BTC 괴리
        if (gold_chg > 1.0 and btc_chg < -1.0) or (gold_chg < -1.0 and btc_chg > 1.0):
            obs.safe_haven_diverging = True

        # 5. Vol Regime Shifting: VIX 급변
        if abs(vix_chg) > 5.0:
            obs.vol_regime_shifting = True

        # 6. Liquidity Absorption Failing: Gold↓↓ (마진콜 신호)
        if gold_chg < -3.0:
            obs.liquidity_absorption_failing = True

        # 7. Narrative Conflicting: 모순적 움직임
        if (spy_chg > 0.5 and vix_chg > 3.0) or (spy_chg < -0.5 and vix_chg < -3.0):
            obs.narrative_conflicting = True

        # 8. Leverage Unwinding: 모든 위험자산↓ + VIX↑
        if spy_chg < -0.5 and btc_chg < -1.0 and vix_chg > 2.0:
            obs.leverage_unwinding = True

        # 9. Flight to Quality: Gold↑ + TLT↑ + SPY↓
        if gold_chg > 0.5 and tlt_chg > 0.3 and spy_chg < 0:
            obs.flight_to_quality = True

        # 10. Risk Seeking: SPY↑ + VIX↓ + BTC↑
        if spy_chg > 0.5 and vix_chg < -2.0 and btc_chg > 1.0:
            obs.risk_seeking_dominant = True

        # ========== 불균형 측정 ==========

        # Liquidity Demand vs Supply
        # Gold↓ + VIX↑ = 수요 > 공급
        obs.liquidity_demand_vs_supply = (vix_chg / 10) - (gold_chg / 5)

        # Policy Credibility Delta
        # TLT↓ despite dovish = 신뢰 하락
        obs.policy_credibility_delta = tlt_chg / 5

        # Risk Appetite Momentum
        obs.risk_appetite_momentum = (spy_chg + btc_chg / 2) / 3 - vix_chg / 10

        # Safe Haven Congestion
        obs.safe_haven_congestion_level = max(0, gold_chg / 3) if gold_chg > 2.0 else 0

        # Correlation Instability
        obs.correlation_instability = abs(gold_chg - btc_chg) / 5

        return obs


# ============================================
# 3. STATE MACHINE ENGINE
# ============================================

class StateMachineEngine:
    """
    Economic State Machine Engine

    - 예측 안 함
    - 추천 안 함
    - 상태 공간만 기록
    """

    def __init__(self):
        self.ontology = STATE_ONTOLOGY
        self.extractor = ObservationExtractor()
        self.state_activations: Dict[str, StateActivation] = {}
        self.interaction_graph = get_interaction_graph()
        self.blocking_graph = get_blocking_graph()

    def process(self, econ_data: dict, date: str) -> Dict:
        """
        하루치 데이터 처리 → State 활성화 계산
        """

        # 1. 관측값 추출
        obs = self.extractor.extract(econ_data, date)

        # 2. State 활성화 계산 (State 간 불균형 기반)
        activations = self._calculate_activations(obs)

        # 3. Blocking 규칙 적용
        activations = self._apply_blocking_rules(activations)

        # 4. Interaction 강화
        activations = self._apply_interaction_boost(activations)

        # 5. 결과 저장
        self.state_activations = activations

        # 6. 전이 윈도우 계산
        transitions = self._calculate_open_transitions(activations)

        # 7. Dominant Interactions 계산
        interactions = self._find_dominant_interactions(activations)

        return {
            "date": date,
            "active_states": self._format_active_states(activations),
            "dominant_interactions": interactions,
            "open_transition_windows": transitions,
            "observation_summary": self._summarize_observations(obs),
        }

    def _calculate_activations(self, obs: MarketObservation) -> Dict[str, StateActivation]:
        """State 간 불균형 기반 활성화 계산"""

        activations = {}

        for state_id, state in self.ontology.items():
            drivers_active = []
            score = 0.0

            # ========== Driver 매칭 (불균형 기반) ==========

            # LIQUIDITY_STRESS
            if state_id == "LIQUIDITY_STRESS":
                if obs.liquidity_demand_vs_supply > 0.3:
                    drivers_active.append("LIQUIDITY_DEMAND > LIQUIDITY_SUPPLY_CAPACITY")
                    score += 0.4
                if obs.liquidity_absorption_failing:
                    drivers_active.append("MARGIN_ABSORPTION_FAILING")
                    score += 0.4
                if obs.safe_asset_liquidation:
                    drivers_active.append("SAFE_ASSET_FORCED_LIQUIDATION")
                    score += 0.3

            # DELEVERAGING_PRESSURE
            elif state_id == "DELEVERAGING_PRESSURE":
                if obs.leverage_unwinding:
                    drivers_active.append("POSITION_UNWINDING_FORCED")
                    score += 0.5
                if obs.correlation_converging:
                    drivers_active.append("MARGIN_CALLS_CASCADING")
                    score += 0.3

            # POLICY_CREDIBILITY_DECAY
            elif state_id == "POLICY_CREDIBILITY_DECAY":
                if obs.policy_signal_ignored:
                    drivers_active.append("POLICY_SIGNAL_IGNORED_BY_MARKET")
                    score += 0.5
                if obs.policy_credibility_delta < -0.2:
                    drivers_active.append("FORWARD_GUIDANCE_FAILURE")
                    score += 0.3

            # RISK_APPETITE_EXPANSION
            elif state_id == "RISK_APPETITE_EXPANSION":
                if obs.risk_seeking_dominant:
                    drivers_active.append("VOL_COMPRESSION_SUSTAINED")
                    score += 0.5
                if obs.risk_appetite_momentum > 0.3:
                    drivers_active.append("CREDIT_SPREADS_TIGHT")
                    score += 0.3

            # RISK_APPETITE_SUPPRESSED
            elif state_id == "RISK_APPETITE_SUPPRESSED":
                if obs.flight_to_quality:
                    drivers_active.append("DEFENSIVE_ROTATION_VISIBLE")
                    score += 0.4
                if obs.risk_appetite_momentum < -0.3:
                    drivers_active.append("HEDGING_DEMAND_RISING")
                    score += 0.3

            # SAFE_HAVEN_DIVERGENCE
            elif state_id == "SAFE_HAVEN_DIVERGENCE":
                if obs.safe_haven_diverging:
                    drivers_active.append("GOLD_BTC_CORRELATION_BREAKDOWN")
                    score += 0.5
                if obs.correlation_instability > 0.4:
                    drivers_active.append("TRADITIONAL_VS_ALTERNATIVE_SPLIT")
                    score += 0.3

            # NARRATIVE_FRAGMENTATION
            elif state_id == "NARRATIVE_FRAGMENTATION":
                if obs.narrative_conflicting:
                    drivers_active.append("CONFLICTING_SIGNALS_DOMINANT")
                    score += 0.5
                if obs.safe_haven_diverging:
                    drivers_active.append("MARKET_CONSENSUS_ABSENT")
                    score += 0.3

            # CORRELATION_REGIME_BREAK
            elif state_id == "CORRELATION_REGIME_BREAK":
                if obs.correlation_instability > 0.5:
                    drivers_active.append("HISTORICAL_CORRELATION_FAILING")
                    score += 0.5

            # MARKET_STRUCTURE_STRAIN
            elif state_id == "MARKET_STRUCTURE_STRAIN":
                if obs.vol_regime_shifting:
                    drivers_active.append("MARKET_MAKING_CAPACITY_REDUCED")
                    score += 0.4

            # DOLLAR_LIQUIDITY_TIGHTENING
            elif state_id == "DOLLAR_LIQUIDITY_TIGHTENING":
                if obs.safe_asset_liquidation and obs.liquidity_demand_vs_supply > 0.2:
                    drivers_active.append("OFFSHORE_DOLLAR_SHORTAGE")
                    score += 0.4

            # CENTRAL_BANK_REACTION_IMMINENT
            elif state_id == "CENTRAL_BANK_REACTION_IMMINENT":
                if obs.vol_regime_shifting and obs.leverage_unwinding:
                    drivers_active.append("FINANCIAL_CONDITIONS_TIGHTENING_FAST")
                    score += 0.5

            # REGIME_TRANSITION_ZONE
            elif state_id == "REGIME_TRANSITION_ZONE":
                if obs.narrative_conflicting or obs.correlation_instability > 0.3:
                    drivers_active.append("MULTIPLE_STATES_ACTIVE")
                    score += 0.3

            # Activation Level 결정
            level = self._score_to_level(score)

            if drivers_active:
                activations[state_id] = StateActivation(
                    state_id=state_id,
                    level=level,
                    drivers_active=drivers_active,
                    confidence=min(score, 1.0)
                )

        return activations

    def _score_to_level(self, score: float) -> ActivationLevel:
        """점수를 활성화 수준으로 변환"""
        if score >= 0.8:
            return ActivationLevel.PEAK
        elif score >= 0.6:
            return ActivationLevel.HIGH
        elif score >= 0.4:
            return ActivationLevel.ELEVATED
        elif score >= 0.2:
            return ActivationLevel.LOW
        else:
            return ActivationLevel.DORMANT

    def _apply_blocking_rules(self, activations: Dict[str, StateActivation]) -> Dict[str, StateActivation]:
        """Blocking 규칙 적용 - 동시 활성화 불가 State 처리"""

        active_ids = set(activations.keys())

        for state_id, activation in list(activations.items()):
            blocked = self.ontology[state_id].blocked_states
            conflicting = active_ids & blocked

            if conflicting:
                # 더 높은 활성화 유지
                for conflict_id in conflicting:
                    if conflict_id in activations:
                        if activations[conflict_id].confidence < activation.confidence:
                            del activations[conflict_id]
                        else:
                            del activations[state_id]
                            break

        return activations

    def _apply_interaction_boost(self, activations: Dict[str, StateActivation]) -> Dict[str, StateActivation]:
        """Interaction 강화 - 동시 활성화 State 간 상호 강화"""

        active_ids = set(activations.keys())

        for state_id, activation in activations.items():
            interactions = self.ontology[state_id].interaction_states
            active_interactions = active_ids & interactions

            if active_interactions:
                # 상호작용하는 State가 있으면 신뢰도 부스트
                boost = len(active_interactions) * 0.1
                activation.confidence = min(1.0, activation.confidence + boost)

        return activations

    def _calculate_open_transitions(self, activations: Dict[str, StateActivation]) -> List[str]:
        """열린 전이 윈도우 계산"""

        transitions = set()

        for state_id, activation in activations.items():
            if activation.level in [ActivationLevel.HIGH, ActivationLevel.PEAK]:
                # 이 State에서 전이 가능한 State들
                interactions = self.ontology[state_id].interaction_states
                transitions.update(interactions)

        # 이미 활성화된 State 제외
        transitions -= set(activations.keys())

        return list(transitions)

    def _find_dominant_interactions(self, activations: Dict[str, StateActivation]) -> List[str]:
        """지배적 상호작용 탐지"""

        interactions = []
        active_ids = list(activations.keys())

        for i, state1 in enumerate(active_ids):
            for state2 in active_ids[i+1:]:
                # 서로 interaction_states에 포함되어 있는지 확인
                if state2 in self.ontology[state1].interaction_states:
                    interactions.append(f"{state1} ↔ {state2}")

        return interactions

    def _format_active_states(self, activations: Dict[str, StateActivation]) -> List[Dict]:
        """활성 State 포맷팅"""

        result = []
        for state_id, activation in sorted(
            activations.items(),
            key=lambda x: x[1].confidence,
            reverse=True
        ):
            if activation.level != ActivationLevel.DORMANT:
                result.append({
                    "state": state_id,
                    "level": activation.level.name,
                    "drivers": activation.drivers_active,
                    "confidence": round(activation.confidence, 2)
                })

        return result

    def _summarize_observations(self, obs: MarketObservation) -> Dict:
        """관측값 요약"""

        signals = []
        if obs.safe_asset_liquidation:
            signals.append("safe_assets_sold_despite_fear")
        if obs.correlation_converging:
            signals.append("correlation_approaching_one")
        if obs.policy_signal_ignored:
            signals.append("policy_signal_ignored")
        if obs.safe_haven_diverging:
            signals.append("safe_haven_diverging")
        if obs.vol_regime_shifting:
            signals.append("vol_regime_shifting")
        if obs.liquidity_absorption_failing:
            signals.append("liquidity_absorption_failing")
        if obs.narrative_conflicting:
            signals.append("narrative_conflicting")
        if obs.leverage_unwinding:
            signals.append("leverage_unwinding")
        if obs.flight_to_quality:
            signals.append("flight_to_quality")
        if obs.risk_seeking_dominant:
            signals.append("risk_seeking_dominant")

        return {
            "active_signals": signals,
            "imbalances": {
                "liquidity": round(obs.liquidity_demand_vs_supply, 2),
                "policy_credibility": round(obs.policy_credibility_delta, 2),
                "risk_appetite": round(obs.risk_appetite_momentum, 2),
                "correlation_stability": round(1 - obs.correlation_instability, 2),
            }
        }

    def get_state_log(self, result: Dict) -> str:
        """
        Daily State Log 형식 출력
        (보고서 아님!)
        """

        lines = []
        lines.append(f"[STATE GRAPH SNAPSHOT - {result['date']}]")
        lines.append("")

        # Active States
        lines.append("ACTIVE STATES:")
        for state in result["active_states"]:
            lines.append(f"  - {state['state']}: {state['level']}")
            for driver in state["drivers"]:
                lines.append(f"      └─ {driver}")

        # Dominant Interactions
        if result["dominant_interactions"]:
            lines.append("")
            lines.append("DOMINANT INTERACTIONS:")
            for interaction in result["dominant_interactions"]:
                lines.append(f"  - {interaction}")

        # Open Transition Windows
        if result["open_transition_windows"]:
            lines.append("")
            lines.append("OPEN TRANSITION WINDOWS:")
            for window in result["open_transition_windows"]:
                lines.append(f"  - {window}")

        # Observation Summary
        lines.append("")
        lines.append("OBSERVED SIGNALS:")
        for signal in result["observation_summary"]["active_signals"]:
            lines.append(f"  - {signal}")

        lines.append("")
        lines.append("IMBALANCE READINGS:")
        imb = result["observation_summary"]["imbalances"]
        lines.append(f"  liquidity_pressure: {imb['liquidity']:+.2f}")
        lines.append(f"  policy_credibility: {imb['policy_credibility']:+.2f}")
        lines.append(f"  risk_appetite: {imb['risk_appetite']:+.2f}")
        lines.append(f"  correlation_stability: {imb['correlation_stability']:.2f}")

        lines.append("")
        lines.append("─" * 50)
        lines.append("SYSTEM NOTE:")
        lines.append("This is not a forecast.")
        lines.append("This is a description of the market state machine at time T.")
        lines.append("─" * 50)

        return "\n".join(lines)


# ============================================
# MAIN
# ============================================

def main():
    import argparse
    import sys

    # 경로 설정
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    # 데이터 로드
    ECON_FILE = os.path.join(BASE_DIR, "data/raw_econ_archive.jsonl")

    econ_data = None
    with open(ECON_FILE, 'r') as f:
        for line in f:
            r = json.loads(line)
            if r.get('date') == args.date:
                econ_data = r.get('econ_data', {})
                break

    if not econ_data:
        print(f"❌ No data for {args.date}")
        return

    # Engine 실행
    engine = StateMachineEngine()
    result = engine.process(econ_data, args.date)

    # State Log 출력
    log = engine.get_state_log(result)
    print(log)

    # JSON 저장
    output_file = os.path.join(BASE_DIR, f"data/state_machine_{args.date}.json")
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Saved: {output_file}")


if __name__ == "__main__":
    main()
