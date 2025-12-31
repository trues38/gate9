#!/usr/bin/env python3
"""
⚠️ DEPRECATED - 2025-12-30
==========================
이 파일은 더 이상 사용되지 않습니다.

대체: engine/unified_pipeline.py

문제:
- Neo4j StateSnapshot 직접 읽기 → stale 데이터 (17시간 전)
- 실시간 시장 데이터와 불일치 (VIX 14.58 but LIQUIDITY_STRESS PEAK)

새 아키텍처:
  unified_pipeline.py가 검증된 데이터로 State 재계산
===========================

State Graph Adjudication Engine v2 [LEGACY]
===================================
NOT an analyst. NOT a forecaster.
A judicial diagnostic system for state conflicts.

Output feels like a court record, not a market newsletter.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class ResolutionStatus(Enum):
    ACTIVE = "RESOLUTION_ACTIVE"
    SUSPENDED = "RESOLUTION_SUSPENDED"
    COMPLETED = "RESOLUTION_COMPLETED"


class TransitionLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class StateActivation:
    state_id: str
    intensity: float
    level: str
    mechanisms: List[str]
    mechanism_count: int
    is_full_activation: bool


@dataclass
class Contradiction:
    id: str
    states_involved: List[str]
    description: str
    why_cannot_persist: str
    what_must_break: str
    winner: Optional[str] = None


@dataclass
class ResolutionPath:
    name: str
    triggers: List[str]
    contradiction_resolved: str
    resolution_mechanism: str
    speed: str  # ABRUPT / CASCADING / SLOW
    condition_count: int


class AdjudicationEngine:
    """State Graph Adjudication Engine"""

    STABILIZER_STATES = {
        "LIQUIDITY_ABUNDANCE",
        "POLICY_CREDIBILITY_STRONG",
        "RISK_APPETITE_EXPANSION",
        "NARRATIVE_CONSENSUS",
    }

    def __init__(self):
        self.driver = None
        self._connect()

    def _connect(self):
        if NEO4J_AVAILABLE:
            uri = os.getenv("NEO4J_ECONOMY_URI", "bolt://localhost:7688")
            user = os.getenv("NEO4J_ECONOMY_USERNAME", "neo4j")
            password = os.getenv("NEO4J_ECONOMY_PASSWORD", "regime2025")
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                with self.driver.session() as session:
                    session.run("RETURN 1")
            except Exception as e:
                print(f"Neo4j connection failed: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def get_active_states(self, date: str) -> List[StateActivation]:
        """Get all active states with mechanisms"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                RETURN s.id as state, a.level as level, a.confidence as conf, a.drivers as drivers
                ORDER BY a.confidence DESC
            """, {"date": date})

            states = []
            for r in result:
                mechanisms = r["drivers"] or []
                # Full activation = all mechanisms firing (assume 3 is full)
                is_full = len(mechanisms) >= 3
                states.append(StateActivation(
                    state_id=r["state"],
                    intensity=r["conf"],
                    level=r["level"],
                    mechanisms=mechanisms,
                    mechanism_count=len(mechanisms),
                    is_full_activation=is_full,
                ))
            return states

    def get_interactions(self, date: str) -> List[Dict]:
        """Get reinforcing interactions between active states"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a1:ACTIVATED]->(s1:StateNode)
                MATCH (snap)-[a2:ACTIVATED]->(s2:StateNode)
                MATCH (s1)-[:CAN_INTERACT_WITH]->(s2)
                WHERE a1.level IN ["ELEVATED", "HIGH", "PEAK"]
                  AND a2.level IN ["ELEVATED", "HIGH", "PEAK"]
                  AND s1.id < s2.id
                RETURN s1.id as state1, s2.id as state2,
                       a1.level as level1, a2.level as level2
            """, {"date": date})
            return [dict(r) for r in result]

    def detect_contradictions(self, states: List[StateActivation], date: str) -> List[Contradiction]:
        """Detect structural contradictions"""
        contradictions = []
        state_ids = [s.state_id for s in states]
        state_map = {s.state_id: s for s in states}

        # Get all driver strings
        all_drivers = []
        for s in states:
            all_drivers.extend(s.mechanisms)
        drivers_str = " ".join(all_drivers)

        # Contradiction 1: Forced Liquidation vs Hedging Demand
        if "SAFE_ASSET_FORCED_LIQUIDATION" in drivers_str and "HEDGING_DEMAND_RISING" in drivers_str:
            contradictions.append(Contradiction(
                id="LIQUIDATION_HEDGE_PARADOX",
                states_involved=["LIQUIDITY_STRESS", "RISK_APPETITE_SUPPRESSED"],
                description="Safe assets being force-sold while hedging demand rises",
                why_cannot_persist="Forced sellers and hedgers compete for same liquidity pool. "
                                   "One side exhausts before the other.",
                what_must_break="Either forced selling exhausts (price stabilizes) or "
                                "hedgers capitulate (protection becomes too expensive)",
            ))

        # Contradiction 2: Dollar Tightening without Capital Flight
        if "DOLLAR_LIQUIDITY_TIGHTENING" in state_ids and "CAPITAL_FLIGHT" not in state_ids:
            if any(s.intensity >= 0.5 for s in states if s.state_id == "DOLLAR_LIQUIDITY_TIGHTENING"):
                contradictions.append(Contradiction(
                    id="INTERNAL_DOLLAR_SHORTAGE",
                    states_involved=["DOLLAR_LIQUIDITY_TIGHTENING"],
                    description="Offshore dollar shortage without EM capital flight activation",
                    why_cannot_persist="Dollar shortage typically triggers EM outflows. "
                                       "Absence suggests either internal US stress or lagging EM reaction.",
                    what_must_break="Either EM capital flight activates (delayed) or "
                                    "dollar shortage is domestic (Fed response likely)",
                ))

        # Contradiction 3: Correlation Break with Low Haven Divergence
        if "CORRELATION_REGIME_BREAK" in state_ids:
            haven_state = state_map.get("SAFE_HAVEN_DIVERGENCE")
            if haven_state and haven_state.level == "LOW":
                contradictions.append(Contradiction(
                    id="CORRELATION_HAVEN_MISMATCH",
                    states_involved=["CORRELATION_REGIME_BREAK", "SAFE_HAVEN_DIVERGENCE"],
                    description="Historical correlations failing but haven divergence reads LOW",
                    why_cannot_persist="Correlation break implies relationship structure is changing. "
                                       "Haven divergence should follow unless break is sector-specific.",
                    what_must_break="Either correlation break is incomplete/reverting or "
                                    "haven divergence measurement is lagging",
                ))

        # Contradiction 4: Peak Stress with Recent Risk Appetite
        with self.driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot)-[a:ACTIVATED {level: "PEAK"}]->(s:StateNode)
                WHERE s.id = "RISK_APPETITE_EXPANSION"
                  AND snap.date < $date
                  AND snap.date >= $start_date
                RETURN snap.date as date
                ORDER BY snap.date DESC
                LIMIT 1
            """, {"date": date, "start_date": (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")})
            recent_risk_peak = result.single()

        if recent_risk_peak and any(s.state_id == "LIQUIDITY_STRESS" and s.level == "PEAK" for s in states):
            contradictions.append(Contradiction(
                id="WHIPLASH_REGIME_FLIP",
                states_involved=["RISK_APPETITE_EXPANSION", "LIQUIDITY_STRESS"],
                description=f"RISK_APPETITE_EXPANSION peaked {recent_risk_peak['date']}, now LIQUIDITY_STRESS at PEAK",
                why_cannot_persist="Rapid regime flip indicates either false stability signal or "
                                   "sudden exogenous shock. System was not in equilibrium.",
                what_must_break="System must choose: either revert to risk appetite (shock absorbed) or "
                                "confirm stress regime (risk appetite was false)",
            ))

        return contradictions

    def determine_resolution_status(self, contradictions: List[Contradiction]) -> Tuple[ResolutionStatus, str]:
        """Classify resolution status"""
        if len(contradictions) == 0:
            return ResolutionStatus.COMPLETED, "No active contradictions. System is in coherent state."

        winners_determined = sum(1 for c in contradictions if c.winner is not None)

        if winners_determined == len(contradictions):
            return ResolutionStatus.COMPLETED, "All contradictions have determined winners."

        if len(contradictions) >= 2 and winners_determined == 0:
            return ResolutionStatus.SUSPENDED, (
                f"{len(contradictions)} contradictions exist with no determined winners. "
                "System is in unstable suspension. This is NOT neutral—it is structurally fragile."
            )

        return ResolutionStatus.ACTIVE, (
            f"{len(contradictions)} contradictions, {winners_determined} resolved. "
            "Resolution in progress but incomplete."
        )

    def compute_transition_zone(self, states: List[StateActivation], interactions: List[Dict]) -> Tuple[TransitionLevel, float, str]:
        """Compute Transition Zone with explicit math"""
        elevated_states = [s for s in states if s.level in ["ELEVATED", "HIGH", "PEAK"]]
        elevated_count = len(elevated_states)

        peak_present = any(s.level == "PEAK" for s in states)
        peak_value = 2.0 if peak_present else 0.0

        interaction_count = len(interactions)
        interaction_value = interaction_count * 0.5

        stabilizers = [s for s in states if s.state_id in self.STABILIZER_STATES and s.level in ["ELEVATED", "HIGH", "PEAK"]]
        stabilizer_count = len(stabilizers)
        stabilizer_value = stabilizer_count * -1.5

        score = elevated_count * 1.0 + peak_value + interaction_value + stabilizer_value

        # Build math string
        math = f"""
  Elevated states: {elevated_count} × 1.0 = {elevated_count:.1f}
  Peak present:    {"Yes" if peak_present else "No"} × 2.0 = {peak_value:.1f}
  Interactions:    {interaction_count} × 0.5 = {interaction_value:.1f}
  Stabilizers:     {stabilizer_count} × -1.5 = {stabilizer_value:.1f}
  ─────────────────────────────────────
  TOTAL SCORE:     {score:.1f}"""

        if score < 2.0:
            level = TransitionLevel.LOW
        elif score < 4.5:
            level = TransitionLevel.MEDIUM
        else:
            level = TransitionLevel.HIGH

        return level, score, math

    def identify_lies(self, states: List[StateActivation], tz_level: TransitionLevel,
                      tz_score: float, contradictions: List[Contradiction]) -> List[Dict]:
        """Identify what the system is lying about"""
        lies = []
        state_map = {s.state_id: s for s in states}

        # Lie 1: REGIME_TRANSITION_ZONE reads LOW when computed is HIGH
        rtz_state = state_map.get("REGIME_TRANSITION_ZONE")
        if rtz_state and rtz_state.level == "LOW":
            if tz_level == TransitionLevel.HIGH:
                lies.append({
                    "claim": "REGIME_TRANSITION_ZONE is reported as LOW",
                    "reality": f"Computed transition score is {tz_score:.1f} (HIGH)",
                    "mechanism": "State label is a static snapshot; computed score uses live structure",
                    "consequence": "System may appear more stable than it is",
                })

        # Lie 2: SAFE_HAVEN_DIVERGENCE LOW with active drivers
        shd_state = state_map.get("SAFE_HAVEN_DIVERGENCE")
        if shd_state and shd_state.level == "LOW":
            if shd_state.mechanism_count >= 2:
                lies.append({
                    "claim": "SAFE_HAVEN_DIVERGENCE reads LOW",
                    "reality": f"{shd_state.mechanism_count} divergence drivers are active",
                    "mechanism": "Threshold-based activation is lagging driver accumulation",
                    "consequence": "Haven divergence may spike without warning",
                })

        # Lie 3: Suspended contradictions appear as "no signal"
        suspended = [c for c in contradictions if c.winner is None]
        if len(suspended) >= 2:
            lies.append({
                "claim": "No clear directional signal",
                "reality": f"{len(suspended)} unresolved contradictions in suspension",
                "mechanism": "Suspension masks structural instability as ambiguity",
                "consequence": "Resolution will be abrupt when it occurs",
            })

        # Lie 4: RISK_APPETITE_SUPPRESSED at LOW while stress is PEAK
        ras_state = state_map.get("RISK_APPETITE_SUPPRESSED")
        ls_state = state_map.get("LIQUIDITY_STRESS")
        if ras_state and ls_state:
            if ras_state.level == "LOW" and ls_state.level == "PEAK":
                lies.append({
                    "claim": "RISK_APPETITE_SUPPRESSED is LOW",
                    "reality": "LIQUIDITY_STRESS is at PEAK intensity",
                    "mechanism": "Risk appetite measurement may lag liquidity stress by 1-2 sessions",
                    "consequence": "Risk suppression is likely underreported",
                })

        return lies

    def generate_resolution_paths(self, states: List[StateActivation],
                                   contradictions: List[Contradiction]) -> Tuple[ResolutionPath, ResolutionPath, str]:
        """Generate two resolution paths with asymmetry analysis"""

        # Path A: Escalation
        path_a = ResolutionPath(
            name="ESCALATION",
            triggers=[
                "VIX sustains > 25 for 2+ sessions",
                "Credit spreads widen > 25bps in 48h",
                "Gold negative while VIX rising (liquidation signature)",
                "MARGIN_CALLS_CASCADING driver activates",
            ],
            contradiction_resolved="LIQUIDATION_HEDGE_PARADOX",
            resolution_mechanism="Forced sellers dominate; hedgers capitulate or are priced out",
            speed="CASCADING",
            condition_count=4,
        )

        # Path B: Absorption
        path_b = ResolutionPath(
            name="ABSORPTION",
            triggers=[
                "VIX < 18 for 2 consecutive sessions",
                "Credit spreads compress or stabilize",
                "Safe asset correlation normalizes",
            ],
            contradiction_resolved="LIQUIDATION_HEDGE_PARADOX",
            resolution_mechanism="Forced selling exhausts; hedging demand satisfied at lower prices",
            speed="SLOW",
            condition_count=3,
        )

        # Asymmetry analysis
        asymmetry = f"""
ASYMMETRY ANALYSIS:

Path A (ESCALATION) requires {path_a.condition_count} conditions.
Path B (ABSORPTION) requires {path_b.condition_count} conditions.

Path B is structurally easier because:
  - Absorption requires only exhaustion of forced sellers
  - Escalation requires active cascade of margin calls
  - Exhaustion is passive; cascade requires new trigger

However, current state favors ESCALATION because:
  - LIQUIDITY_STRESS is at PEAK (not declining)
  - DOLLAR_LIQUIDITY_TIGHTENING reinforces stress
  - No stabilizer states are active

Asymmetry Verdict: ESCALATION has momentum; ABSORPTION requires intervention or exhaustion.
"""

        return path_a, path_b, asymmetry

    def analyze_first_failure(self, date: str) -> Tuple[Optional[str], str]:
        """Analyze what historically fails first"""
        with self.driver.session() as session:
            # Find PEAK states in current date's pattern that have historical precedent
            result = session.run("""
                MATCH (current:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE a.level IN ["HIGH", "PEAK", "ELEVATED"]
                WITH collect(s.id) as current_states

                MATCH (past:StateSnapshot)-[pa:ACTIVATED {level: "PEAK"}]->(ps:StateNode)
                WHERE past.date < $date
                  AND ps.id IN current_states

                OPTIONAL MATCH (past)-[:NEXT_DAY]->(next:StateSnapshot)-[na:ACTIVATED]->(ns:StateNode)
                WHERE na.level IN ["HIGH", "PEAK"]

                RETURN ps.id as peak_state, past.date as peak_date,
                       collect(DISTINCT ns.id) as persisted_states
                ORDER BY past.date DESC
                LIMIT 10
            """, {"date": date})

            history = [dict(r) for r in result]

        if not history:
            return None, """
DATA INSUFFICIENT FOR FIRST FAILURE ANALYSIS

Missing:
  - No historical PEAK states matching current pattern found
  - December data may be too short for reliable sequence analysis

Why This Matters:
  - First failure point prediction requires pattern → outcome sequences
  - Without outcomes, we cannot determine which state breaks first
  - Current stress may be novel (no historical analog in this dataset)

Required Data:
  - Longer historical window (6+ months)
  - PEAK states with documented next-day outcomes
"""

        # Analyze patterns
        from collections import Counter
        peak_states = [h["peak_state"] for h in history]
        most_common = Counter(peak_states).most_common(1)

        if most_common:
            first_failure = most_common[0][0]
            frequency = most_common[0][1]

            # Check persistence
            persisted = sum(1 for h in history if h["peak_state"] in h.get("persisted_states", []))
            persistence_rate = persisted / len(history) if history else 0

            analysis = f"""
FIRST FAILURE POINT: {first_failure}
Historical Frequency: {frequency} occurrences in similar patterns
Persistence Rate: {persistence_rate:.0%} (state remained elevated after PEAK)

Historical Sequences:
"""
            for h in history[:5]:
                persisted_str = "→ PERSISTED" if h["peak_state"] in h.get("persisted_states", []) else "→ RESOLVED"
                analysis += f"  {h['peak_date']}: {h['peak_state']} {persisted_str}\n"

            return first_failure, analysis

        return None, "Insufficient data for first failure analysis."

    def generate_watch_conditions(self, states: List[StateActivation],
                                   contradictions: List[Contradiction]) -> List[Dict]:
        """Generate 48-72h watch conditions"""
        conditions = []

        # VIX threshold
        conditions.append({
            "trigger": "VIX > 25 sustained for 2 sessions",
            "state_activates": "DELEVERAGING_PRESSURE",
            "implication": "Margin call cascade begins; forced position unwinding",
        })

        # Gold liquidation signature
        conditions.append({
            "trigger": "Gold -2% while VIX +10%",
            "state_activates": "MARKET_STRUCTURE_STRAIN",
            "implication": "Liquidity stress forcing safe asset sales; market making withdrawn",
        })

        # Credit spread
        conditions.append({
            "trigger": "Investment grade spreads widen > 20bps in 48h",
            "state_activates": "CENTRAL_BANK_REACTION_IMMINENT",
            "implication": "Credit stress visible; policy intervention becomes likely",
        })

        # Contradiction resolution
        for c in contradictions:
            if c.winner is None:
                conditions.append({
                    "trigger": f"Contradiction {c.id} resolves toward either side",
                    "state_activates": "Resolution-dependent",
                    "implication": c.what_must_break,
                })

        return conditions

    def generate_adjudication(self, date: str) -> str:
        """Generate full adjudication log"""

        states = self.get_active_states(date)
        interactions = self.get_interactions(date)
        contradictions = self.detect_contradictions(states, date)
        resolution_status, resolution_reason = self.determine_resolution_status(contradictions)
        tz_level, tz_score, tz_math = self.compute_transition_zone(states, interactions)
        lies = self.identify_lies(states, tz_level, tz_score, contradictions)
        path_a, path_b, asymmetry = self.generate_resolution_paths(states, contradictions)
        first_failure, failure_analysis = self.analyze_first_failure(date)
        watch_conditions = self.generate_watch_conditions(states, contradictions)

        # Build report
        report = f"""[STATE CONFLICT + RESOLUTION LOG — {date}]

{'='*80}
1. DOMINANT STATE PRESSURES
{'='*80}

"""
        dominant = [s for s in states if s.intensity >= 0.5]
        if dominant:
            for s in dominant:
                activation_type = "FULL ACTIVATION" if s.is_full_activation else f"PARTIAL ({s.mechanism_count}/3 mechanisms)"
                report += f"""STATE: {s.state_id}
  Intensity: {s.intensity:.2f}
  Level: {s.level}
  Activation: {activation_type}
  Mechanisms:
"""
                for m in s.mechanisms:
                    report += f"    • {m}\n"
                report += "\n"

                if s.mechanism_count >= 3:
                    report += "  ⚠️ ALL MECHANISMS FIRING SIMULTANEOUSLY\n\n"
        else:
            report += "No states with intensity ≥ 0.5\n\n"

        report += f"""{'='*80}
2. STRUCTURAL CONTRADICTIONS
{'='*80}

"""
        if contradictions:
            for c in contradictions:
                report += f"""[{c.id}]
  States Involved: {', '.join(c.states_involved)}
  Description: {c.description}

  Why Cannot Persist:
    {c.why_cannot_persist}

  What Must Break:
    {c.what_must_break}

  Winner Determined: {"No" if c.winner is None else c.winner}

"""
        else:
            report += "No structural contradictions detected.\n\n"

        report += f"""{'='*80}
3. RESOLUTION STATUS
{'='*80}

Status: {resolution_status.value}

{resolution_reason}

"""
        if resolution_status == ResolutionStatus.SUSPENDED:
            report += """⚠️ SUSPENSION WARNING:
This is NOT a neutral state. The system is holding multiple incompatible
configurations simultaneously. Resolution, when it occurs, will be abrupt.

"""

        report += f"""{'='*80}
4. TRANSITION ZONE COMPUTATION
{'='*80}

{tz_math}

Classification: {tz_level.value}

"""

        report += f"""{'='*80}
5. WHAT THE SYSTEM IS LYING ABOUT
{'='*80}

"""
        if lies:
            for i, lie in enumerate(lies, 1):
                report += f"""LIE #{i}: {lie['claim']}
  Reality: {lie['reality']}
  Mechanism: {lie['mechanism']}
  Consequence: {lie['consequence']}

"""
        else:
            report += """No lies detected.

This is rare. Either:
  - System is in genuine coherence (unlikely during stress)
  - Detection mechanisms are insufficient
  - Lies exist but are not yet measurable

"""

        report += f"""{'='*80}
6. RESOLUTION PATHS
{'='*80}

PATH A: {path_a.name}
  Speed: {path_a.speed}
  Contradiction Resolved: {path_a.contradiction_resolved}
  Resolution Mechanism: {path_a.resolution_mechanism}

  Triggers Required:
"""
        for t in path_a.triggers:
            report += f"    [ ] {t}\n"

        report += f"""
PATH B: {path_b.name}
  Speed: {path_b.speed}
  Contradiction Resolved: {path_b.contradiction_resolved}
  Resolution Mechanism: {path_b.resolution_mechanism}

  Triggers Required:
"""
        for t in path_b.triggers:
            report += f"    [ ] {t}\n"

        report += f"""
{asymmetry}
"""

        report += f"""{'='*80}
7. FIRST FAILURE POINT ANALYSIS
{'='*80}
{failure_analysis}
"""

        report += f"""{'='*80}
8. ACTIONABLE WATCH CONDITIONS (48-72H)
{'='*80}

"""
        for i, w in enumerate(watch_conditions, 1):
            report += f"""[{i}] {w['trigger']}
    → Activates: {w['state_activates']}
    → Implication: {w['implication']}

"""

        report += f"""{'='*80}
9. FINAL ADJUDICATION STATEMENT
{'='*80}

"""
        # Build final statement based on status
        undecided = [c.id for c in contradictions if c.winner is None]
        sensitivity = "LIQUIDITY_STRESS mechanisms" if any(s.state_id == "LIQUIDITY_STRESS" and s.level == "PEAK" for s in states) else "contradiction resolution"

        if resolution_status == ResolutionStatus.SUSPENDED:
            report += f"""The system currently cannot decide the outcome of {len(undecided)} contradiction(s):
{', '.join(undecided)}.

The system is most sensitive to {sensitivity}. Current PEAK intensity on primary
stress state indicates elevated fragility.

Rapid resolution would be forced by: VIX breach above 25 (escalation path) or
sustained safe asset stabilization with credit spread compression (absorption path).

Until resolution occurs, the suspended state itself is the signal. Treat ambiguity
as instability, not neutrality.
"""
        elif resolution_status == ResolutionStatus.ACTIVE:
            report += f"""Resolution is in progress but incomplete. {len([c for c in contradictions if c.winner])} of
{len(contradictions)} contradictions have determined winners.

The system is most sensitive to remaining contradiction resolution. Partial
resolution may create false stability signals. Monitor for asymmetric breaks.
"""
        else:
            report += """The system is in coherent state with no active contradictions. This is either
genuine stability or measurement artifact. In stress regimes, coherence is
typically temporary. Monitor for new contradiction emergence.
"""

        report += f"""
{'='*80}
ENGINE METADATA
{'='*80}
Engine: State Graph Adjudication Engine v2.0
Data Source: Neo4j State Graph (bolt://localhost:7688)
Snapshot Date: {date}
States Analyzed: {len(states)}
Dominant States (≥0.5): {len(dominant)}
Contradictions: {len(contradictions)}
Resolution Status: {resolution_status.value}
Transition Zone: {tz_level.value} ({tz_score:.1f})
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    engine = AdjudicationEngine()
    try:
        report = engine.generate_adjudication(args.date)
        print(report)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\n✅ Saved: {args.output}")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
