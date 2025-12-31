#!/usr/bin/env python3
"""
State Conflict + Resolution Engine
===================================
GraphRAG-first Economic Regime Intelligence

NOT a report generator.
A state conflict detector with resolution logic.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class TransitionLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class StateMetrics:
    """State duration and decay metrics"""
    state_id: str
    days_active: int = 0
    days_since_peak: int = 0
    peak_count_this_month: int = 0
    half_life: float = 3.0  # default decay in days
    persistence_score: float = 0.0
    last_peak_date: Optional[str] = None


@dataclass
class Contradiction:
    """Structural contradiction with resolution logic"""
    id: str
    state_a: str
    state_b: str
    description: str
    quant_proxy_a: str  # Supabase column for state A
    quant_proxy_b: str  # Supabase column for state B
    winner: Optional[str] = None
    winner_evidence: Optional[str] = None
    resolution_watch: bool = False
    watch_timer: int = 0  # sessions until forced resolution


@dataclass
class TransitionZone:
    """Computed Transition Zone"""
    level: TransitionLevel
    score: float
    elevated_count: int
    peak_present: bool
    interaction_count: int
    stabilizer_count: int
    breakdown: Dict


class ConflictResolutionEngine:
    """State Conflict + Resolution Engine"""

    # Stabilizer states that reduce transition pressure
    STABILIZER_STATES = {
        "LIQUIDITY_ABUNDANCE",
        "POLICY_CREDIBILITY_STRONG",
        "RISK_APPETITE_EXPANSION",
        "NARRATIVE_CONSENSUS",
    }

    # Contradiction definitions with quant proxies
    CONTRADICTION_RULES = [
        {
            "id": "SAFE_ASSET_PARADOX",
            "state_a": "SAFE_ASSET_FORCED_LIQUIDATION",
            "state_b": "HEDGING_DEMAND_RISING",
            "description": "Selling safe assets while buying protection",
            "quant_proxy_a": "gold_pct_change",  # negative = liquidation
            "quant_proxy_b": "vix_level",  # high = hedging demand
            "winner_logic": "gold_pct_change < -1 AND vix_level > 20 => LIQUIDATION_WINS",
        },
        {
            "id": "DOLLAR_FLIGHT_DISCONNECT",
            "state_a": "DOLLAR_LIQUIDITY_TIGHTENING",
            "state_b": "CAPITAL_FLIGHT",
            "description": "Dollar shortage without EM capital flight",
            "quant_proxy_a": "dxy_level",
            "quant_proxy_b": "em_spread",  # proxy for EM stress
            "winner_logic": "dxy > 105 AND em_spread < 400 => INTERNAL_SHORTAGE",
        },
        {
            "id": "CORRELATION_HAVEN_MISMATCH",
            "state_a": "CORRELATION_REGIME_BREAK",
            "state_b": "SAFE_HAVEN_DIVERGENCE",
            "description": "Correlation breaking but haven divergence low",
            "quant_proxy_a": "spx_gold_corr_30d",
            "quant_proxy_b": "gold_btc_corr_30d",
            "winner_logic": "abs(spx_gold_corr) > 0.5 => CORRELATION_INTACT",
        },
    ]

    def __init__(self):
        self.neo4j_driver = None
        self.supabase_client = None
        self._connect()

    def _connect(self):
        """Connect to data sources"""
        # Neo4j
        if NEO4J_AVAILABLE:
            uri = os.getenv("NEO4J_ECONOMY_URI", "bolt://localhost:7688")
            user = os.getenv("NEO4J_ECONOMY_USERNAME", "neo4j")
            password = os.getenv("NEO4J_ECONOMY_PASSWORD", "regime2025")
            try:
                self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
                with self.neo4j_driver.session() as session:
                    session.run("RETURN 1")
                print("✅ Neo4j connected")
            except Exception as e:
                print(f"⚠️ Neo4j failed: {e}")

        # Supabase
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
            if url and key:
                try:
                    self.supabase_client = create_client(url, key)
                    print("✅ Supabase connected")
                except Exception as e:
                    print(f"⚠️ Supabase failed: {e}")

    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()

    # =========================================
    # 1. TRANSITION ZONE COMPUTATION
    # =========================================

    def compute_transition_zone(self, date: str) -> TransitionZone:
        """
        Compute REGIME_TRANSITION_ZONE as a proper metric.

        Score = (elevated_count * 1.0)
              + (peak_present * 2.0)
              + (interaction_count * 0.5)
              - (stabilizer_count * 1.5)

        Levels:
        - LOW: score < 2
        - MEDIUM: 2 <= score < 4
        - HIGH: 4 <= score < 6
        - CRITICAL: score >= 6
        """
        with self.neo4j_driver.session() as session:
            # Count ELEVATED+ states
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE a.level IN ["ELEVATED", "HIGH", "PEAK"]
                RETURN s.id as state, a.level as level
            """, {"date": date})
            elevated_states = [dict(r) for r in result]
            elevated_count = len(elevated_states)

            # Check for PEAK
            peak_present = any(s["level"] == "PEAK" for s in elevated_states)

            # Count reinforcing interactions
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a1:ACTIVATED]->(s1:StateNode)
                MATCH (snap)-[a2:ACTIVATED]->(s2:StateNode)
                MATCH (s1)-[:CAN_INTERACT_WITH]->(s2)
                WHERE a1.level IN ["ELEVATED", "HIGH", "PEAK"]
                  AND a2.level IN ["ELEVATED", "HIGH", "PEAK"]
                  AND s1.id < s2.id
                RETURN s1.id as state1, s2.id as state2
            """, {"date": date})
            interactions = [dict(r) for r in result]
            interaction_count = len(interactions)

            # Count stabilizers
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE s.id IN $stabilizers
                  AND a.level IN ["ELEVATED", "HIGH", "PEAK"]
                RETURN count(s) as cnt
            """, {"date": date, "stabilizers": list(self.STABILIZER_STATES)})
            stabilizer_count = result.single()["cnt"]

        # Compute score
        score = (
            elevated_count * 1.0 +
            (2.0 if peak_present else 0.0) +
            interaction_count * 0.5 -
            stabilizer_count * 1.5
        )

        # Determine level
        if score < 2:
            level = TransitionLevel.LOW
        elif score < 4:
            level = TransitionLevel.MEDIUM
        elif score < 6:
            level = TransitionLevel.HIGH
        else:
            level = TransitionLevel.CRITICAL

        return TransitionZone(
            level=level,
            score=round(score, 2),
            elevated_count=elevated_count,
            peak_present=peak_present,
            interaction_count=interaction_count,
            stabilizer_count=stabilizer_count,
            breakdown={
                "elevated_states": [s["state"] for s in elevated_states],
                "interactions": interactions,
            }
        )

    # =========================================
    # 2. STATE DURATION / DECAY
    # =========================================

    def compute_state_duration(self, state_id: str, current_date: str) -> StateMetrics:
        """Compute duration and decay metrics for a state"""

        with self.neo4j_driver.session() as session:
            # Find all activations of this state in December
            result = session.run("""
                MATCH (snap:StateSnapshot)-[a:ACTIVATED]->(s:StateNode {id: $state_id})
                WHERE snap.date <= $current_date
                RETURN snap.date as date, a.level as level
                ORDER BY snap.date DESC
            """, {"state_id": state_id, "current_date": current_date})
            activations = [dict(r) for r in result]

        if not activations:
            return StateMetrics(state_id=state_id)

        # Calculate days_active (consecutive from today)
        days_active = 0
        dates = sorted([a["date"] for a in activations], reverse=True)

        # Check if active today
        if dates[0] != current_date:
            days_active = 0
        else:
            # Count consecutive days
            current = datetime.strptime(current_date, "%Y-%m-%d")
            for d in dates:
                dt = datetime.strptime(d, "%Y-%m-%d")
                if (current - dt).days <= days_active + 1:
                    days_active += 1
                    current = dt
                else:
                    break

        # Find peaks
        peaks = [a for a in activations if a["level"] == "PEAK"]
        peak_count = len(peaks)
        last_peak_date = peaks[0]["date"] if peaks else None

        # Days since peak
        if last_peak_date:
            peak_dt = datetime.strptime(last_peak_date, "%Y-%m-%d")
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            days_since_peak = (current_dt - peak_dt).days
        else:
            days_since_peak = 999

        # Persistence score (higher = more persistent)
        # Based on activation frequency and peak history
        total_days = len(set([a["date"] for a in activations]))
        persistence_score = min(1.0, total_days / 10) * (1 + peak_count * 0.2)

        return StateMetrics(
            state_id=state_id,
            days_active=days_active,
            days_since_peak=days_since_peak,
            peak_count_this_month=peak_count,
            persistence_score=round(persistence_score, 2),
            last_peak_date=last_peak_date,
        )

    # =========================================
    # 3. CONTRADICTION RESOLUTION
    # =========================================

    def get_quant_data(self, date: str) -> Dict:
        """Get quant data from Supabase for contradiction resolution"""

        if not self.supabase_client:
            return {}

        try:
            # Try to get from raw_econ_archive or similar table
            result = self.supabase_client.table("econ_daily_snapshot").select("*").eq("date", date).execute()
            if result.data:
                return result.data[0]
        except:
            pass

        # Fallback: try local file
        try:
            archive_path = os.path.join(BASE_DIR, "data/raw_econ_archive.jsonl")
            with open(archive_path, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("date") == date:
                        return record.get("econ_data", {})
        except:
            pass

        return {}

    def resolve_contradictions(self, date: str, active_states: List[str]) -> List[Contradiction]:
        """Identify and attempt to resolve contradictions"""

        quant_data = self.get_quant_data(date)
        contradictions = []

        # Check active driver conditions (not just state labels)
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                RETURN s.id as state, a.drivers as drivers, a.level as level
            """, {"date": date})
            state_drivers = {r["state"]: r["drivers"] for r in result}

        # Check each contradiction rule
        for rule in self.CONTRADICTION_RULES:
            # Check if contradicting conditions exist in drivers
            drivers_flat = " ".join([" ".join(d or []) for d in state_drivers.values()])

            if rule["id"] == "SAFE_ASSET_PARADOX":
                # Check for forced liquidation + hedging demand
                has_liquidation = "SAFE_ASSET_FORCED_LIQUIDATION" in drivers_flat
                has_hedging = "HEDGING_DEMAND_RISING" in drivers_flat

                if has_liquidation and has_hedging:
                    c = Contradiction(
                        id=rule["id"],
                        state_a=rule["state_a"],
                        state_b=rule["state_b"],
                        description=rule["description"],
                        quant_proxy_a=rule["quant_proxy_a"],
                        quant_proxy_b=rule["quant_proxy_b"],
                    )

                    # Try to resolve with quant data
                    gold_change = quant_data.get("gold_pct_change") or quant_data.get("gold", {}).get("pct_change")
                    vix_level = quant_data.get("vix_level") or quant_data.get("vix", {}).get("value")

                    if gold_change is not None and vix_level is not None:
                        if gold_change < -1 and vix_level > 20:
                            c.winner = "LIQUIDATION_WINS"
                            c.winner_evidence = f"Gold: {gold_change:.1f}%, VIX: {vix_level:.1f}"
                        elif gold_change > 0 and vix_level > 25:
                            c.winner = "HEDGING_WINS"
                            c.winner_evidence = f"Gold: {gold_change:.1f}%, VIX: {vix_level:.1f}"
                        else:
                            c.resolution_watch = True
                            c.watch_timer = 2
                    else:
                        c.resolution_watch = True
                        c.watch_timer = 2
                        c.winner_evidence = "INSUFFICIENT_QUANT_DATA"

                    contradictions.append(c)

            elif rule["id"] == "DOLLAR_FLIGHT_DISCONNECT":
                has_dollar = "DOLLAR_LIQUIDITY_TIGHTENING" in active_states
                has_flight = "CAPITAL_FLIGHT" in active_states

                if has_dollar and not has_flight:
                    c = Contradiction(
                        id=rule["id"],
                        state_a=rule["state_a"],
                        state_b=rule["state_b"],
                        description=rule["description"],
                        quant_proxy_a=rule["quant_proxy_a"],
                        quant_proxy_b=rule["quant_proxy_b"],
                    )

                    dxy = quant_data.get("dxy", {}).get("value")

                    if dxy:
                        if dxy > 105:
                            c.winner = "INTERNAL_SHORTAGE"
                            c.winner_evidence = f"DXY: {dxy:.1f} (EM not yet stressed)"
                        else:
                            c.resolution_watch = True
                            c.watch_timer = 1
                    else:
                        c.resolution_watch = True
                        c.watch_timer = 2

                    contradictions.append(c)

            elif rule["id"] == "CORRELATION_HAVEN_MISMATCH":
                has_corr_break = "CORRELATION_REGIME_BREAK" in active_states
                haven_div_low = "SAFE_HAVEN_DIVERGENCE" in active_states  # we'll check level

                if has_corr_break:
                    with self.neo4j_driver.session() as session:
                        result = session.run("""
                            MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode {id: "SAFE_HAVEN_DIVERGENCE"})
                            RETURN a.level as level, a.confidence as conf
                        """, {"date": date})
                        haven_data = result.single()

                    if haven_data and haven_data["level"] == "LOW":
                        c = Contradiction(
                            id=rule["id"],
                            state_a=rule["state_a"],
                            state_b=rule["state_b"],
                            description=rule["description"],
                            quant_proxy_a=rule["quant_proxy_a"],
                            quant_proxy_b=rule["quant_proxy_b"],
                        )
                        c.resolution_watch = True
                        c.watch_timer = 2
                        c.winner_evidence = "HAVEN_DIVERGENCE_LAGGING"
                        contradictions.append(c)

        return contradictions

    # =========================================
    # 4. FIRST FAILURE POINT ANALYSIS
    # =========================================

    def analyze_first_failure(self, date: str) -> Dict:
        """Determine what breaks first based on graph history"""

        with self.neo4j_driver.session() as session:
            # Find similar past patterns and what failed first
            result = session.run("""
                MATCH (current:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE a.level IN ["HIGH", "PEAK", "ELEVATED"]
                WITH collect(s.id) as current_states

                // Find past similar patterns
                MATCH (past:StateSnapshot)-[a2:ACTIVATED {level: "PEAK"}]->(peak_state:StateNode)
                WHERE past.date < $date
                  AND peak_state.id IN current_states

                // What happened next?
                OPTIONAL MATCH (past)-[:NEXT_DAY]->(next:StateSnapshot)-[na:ACTIVATED]->(ns:StateNode)
                WHERE na.level IN ["HIGH", "PEAK", "ELEVATED"]

                RETURN past.date as peak_date,
                       peak_state.id as peak_state,
                       collect(DISTINCT ns.id) as next_states
                ORDER BY past.date DESC
                LIMIT 5
            """, {"date": date})

            failures = [dict(r) for r in result]

        if not failures:
            return {"status": "NO_HISTORICAL_PEAK_MATCH"}

        # Analyze failure patterns
        failure_sequences = []
        for f in failures:
            failure_sequences.append({
                "peak_date": f["peak_date"],
                "peak_state": f["peak_state"],
                "next_states": f["next_states"],
                "persistence": f["peak_state"] in f["next_states"],
            })

        # Most common first failure
        peak_states = [f["peak_state"] for f in failures]
        from collections import Counter
        most_common = Counter(peak_states).most_common(1)

        return {
            "status": "PATTERN_FOUND",
            "most_likely_first_failure": most_common[0][0] if most_common else None,
            "frequency": most_common[0][1] if most_common else 0,
            "historical_sequences": failure_sequences,
        }

    # =========================================
    # 5. RESOLUTION PATHS
    # =========================================

    def generate_resolution_paths(self, date: str, tz: TransitionZone, contradictions: List[Contradiction]) -> Dict:
        """Generate two resolution paths with trigger checklists"""

        with self.neo4j_driver.session() as session:
            # Get open transitions
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[:TRANSITION_OPEN]->(s:StateNode)
                RETURN s.id as state
            """, {"date": date})
            open_transitions = [r["state"] for r in result]

            # Get current peak state
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED {level: "PEAK"}]->(s:StateNode)
                RETURN s.id as state, a.drivers as drivers
            """, {"date": date})
            peak_data = result.single()

        peak_state = peak_data["state"] if peak_data else None
        peak_drivers = peak_data["drivers"] if peak_data else []

        # Path A: Escalation (transition fires)
        path_a = {
            "name": "ESCALATION",
            "description": "Stress intensifies, transition fires",
            "trigger_checklist": [],
            "probability_conditions": [],
        }

        if "DELEVERAGING_PRESSURE" in open_transitions:
            path_a["trigger_checklist"].append("VIX > 25 for 2 consecutive sessions")
            path_a["trigger_checklist"].append("Credit spreads widen > 20bps in 48h")
            path_a["probability_conditions"].append("If MARGIN_CALLS_CASCADING driver activates")

        if peak_state == "LIQUIDITY_STRESS":
            path_a["trigger_checklist"].append("TED spread > 50bps")
            path_a["trigger_checklist"].append("Gold down while VIX up (liquidation signature)")

        # Path B: Resolution (stress absorbed)
        path_b = {
            "name": "ABSORPTION",
            "description": "Stress absorbed, reversion to stability",
            "trigger_checklist": [],
            "probability_conditions": [],
        }

        path_b["trigger_checklist"].append("VIX < 18 for 2 consecutive sessions")
        path_b["trigger_checklist"].append("Safe asset correlation normalizes (SPX-Gold < 0.3)")
        path_b["trigger_checklist"].append("Credit spreads stable or compressing")

        if contradictions:
            for c in contradictions:
                if c.resolution_watch:
                    path_b["probability_conditions"].append(
                        f"Contradiction {c.id} resolves toward stability"
                    )

        return {
            "path_a": path_a,
            "path_b": path_b,
            "current_bias": "ESCALATION" if tz.level in [TransitionLevel.HIGH, TransitionLevel.CRITICAL] else "NEUTRAL",
        }

    # =========================================
    # 6. GENERATE FULL REPORT
    # =========================================

    def generate_report(self, date: str) -> str:
        """Generate the new format report"""

        # Get active states
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                RETURN s.id as state, a.level as level, a.confidence as conf, a.drivers as drivers
                ORDER BY a.confidence DESC
            """, {"date": date})
            active_states_data = [dict(r) for r in result]

        active_states = [s["state"] for s in active_states_data]

        # Compute all metrics
        tz = self.compute_transition_zone(date)
        contradictions = self.resolve_contradictions(date, active_states)
        first_failure = self.analyze_first_failure(date)
        resolution_paths = self.generate_resolution_paths(date, tz, contradictions)

        # Get state durations for key states
        state_metrics = {}
        for s in active_states_data:
            if s["level"] in ["PEAK", "HIGH", "ELEVATED"]:
                state_metrics[s["state"]] = self.compute_state_duration(s["state"], date)

        # Get quant data for evidence
        quant_data = self.get_quant_data(date)

        # Build report
        report = f"""[STATE CONFLICT + RESOLUTION LOG — {date}]

================================================================================
TRANSITION ZONE: {tz.level.value} (score: {tz.score})
================================================================================

Computation:
  - ELEVATED+ states: {tz.elevated_count} × 1.0 = {tz.elevated_count:.1f}
  - PEAK present: {"Yes" if tz.peak_present else "No"} × 2.0 = {2.0 if tz.peak_present else 0.0:.1f}
  - Reinforcing interactions: {tz.interaction_count} × 0.5 = {tz.interaction_count * 0.5:.1f}
  - Stabilizer states: {tz.stabilizer_count} × -1.5 = {tz.stabilizer_count * -1.5:.1f}
  - TOTAL SCORE: {tz.score}

Active ELEVATED+ States: {tz.breakdown['elevated_states']}
Firing Interactions: {tz.breakdown['interactions']}

================================================================================
SECTION A: WHAT BREAKS FIRST?
================================================================================

"""
        if first_failure["status"] == "PATTERN_FOUND":
            report += f"""Primary Failure Point: {first_failure['most_likely_first_failure']}
Historical Frequency: {first_failure['frequency']} occurrences in similar patterns

Evidence from Graph:
"""
            for seq in first_failure["historical_sequences"][:3]:
                persistence = "PERSISTED" if seq["persistence"] else "RESOLVED"
                report += f"  - {seq['peak_date']}: {seq['peak_state']} peaked → {persistence}\n"
                report += f"    Next states: {seq['next_states']}\n"
        else:
            report += "INSUFFICIENT HISTORICAL DATA FOR FAILURE POINT PREDICTION\n"

        # State durations
        report += "\nState Duration Metrics:\n"
        for state_id, metrics in state_metrics.items():
            if metrics.days_active > 0:
                peak_info = f" (peak {metrics.days_since_peak}d ago)" if metrics.last_peak_date else ""
                report += f"  - {state_id}: Day {metrics.days_active} of activation{peak_info}\n"
                report += f"    Persistence score: {metrics.persistence_score}, Monthly peaks: {metrics.peak_count_this_month}\n"

        report += f"""
================================================================================
SECTION B: WHAT IS THE MARKET LYING ABOUT?
================================================================================

"""
        # Check for lies based on contradictions and state inconsistencies
        lies_found = []

        # Lie 1: Old State Machine reported REGIME_TRANSITION_ZONE as LOW
        # Check what the old engine said
        for s in active_states_data:
            if s["state"] == "REGIME_TRANSITION_ZONE" and s["level"] == "LOW":
                # But our new computation says otherwise
                if tz.level in [TransitionLevel.HIGH, TransitionLevel.CRITICAL]:
                    lies_found.append({
                        "claim": "Old State Machine reported REGIME_TRANSITION_ZONE as LOW",
                        "reality": f"New computation: {tz.level.value} (score: {tz.score})",
                        "quant_proof": f"{tz.elevated_count} ELEVATED+ states, {tz.interaction_count} interactions, PEAK present: {tz.peak_present}",
                    })

        # Lie 2: Safe haven divergence low despite drivers
        for s in active_states_data:
            if s["state"] == "SAFE_HAVEN_DIVERGENCE" and s["level"] == "LOW":
                drivers = s.get("drivers", [])
                if drivers and len(drivers) >= 2:
                    lies_found.append({
                        "claim": "SAFE_HAVEN_DIVERGENCE at LOW",
                        "reality": f"Drivers active: {drivers}",
                        "quant_proof": "Multiple divergence drivers firing but state reads LOW",
                    })

        # Lie 3: Recent RISK_APPETITE_EXPANSION
        for state_id, metrics in state_metrics.items():
            if metrics.last_peak_date and metrics.days_since_peak < 14:
                if state_id in ["RISK_APPETITE_EXPANSION", "LIQUIDITY_ABUNDANCE"]:
                    current_stress = any(s["state"] == "LIQUIDITY_STRESS" for s in active_states_data)
                    if current_stress:
                        lies_found.append({
                            "claim": f"{state_id} peaked {metrics.days_since_peak} days ago",
                            "reality": "Current state shows LIQUIDITY_STRESS at PEAK",
                            "quant_proof": f"Stability signal from {metrics.last_peak_date} was false",
                        })

        if lies_found:
            for i, lie in enumerate(lies_found, 1):
                report += f"""Lie #{i}: {lie['claim']}
  Reality: {lie['reality']}
  Quant Proof: {lie['quant_proof']}

"""
        else:
            report += "No state inconsistencies detected.\n\n"

        report += f"""================================================================================
SECTION C: TWO RESOLUTION PATHS
================================================================================

PATH A: {resolution_paths['path_a']['name']}
{resolution_paths['path_a']['description']}

Trigger Checklist (48h):
"""
        for trigger in resolution_paths['path_a']['trigger_checklist']:
            report += f"  [ ] {trigger}\n"

        report += "\nProbability Conditions:\n"
        for cond in resolution_paths['path_a']['probability_conditions']:
            report += f"  - {cond}\n"

        report += f"""
PATH B: {resolution_paths['path_b']['name']}
{resolution_paths['path_b']['description']}

Trigger Checklist (48h):
"""
        for trigger in resolution_paths['path_b']['trigger_checklist']:
            report += f"  [ ] {trigger}\n"

        report += "\nProbability Conditions:\n"
        for cond in resolution_paths['path_b']['probability_conditions']:
            report += f"  - {cond}\n"

        report += f"""
Current System Bias: {resolution_paths['current_bias']}

================================================================================
SECTION D: ACTIONABLE TRIGGERS FOR NEXT 48H
================================================================================

CONTRADICTION WATCH LIST:
"""
        if contradictions:
            for c in contradictions:
                status = "RESOLVED" if c.winner else f"WATCH ({c.watch_timer} sessions)"
                report += f"""
[{c.id}]
  Status: {status}
  States: {c.state_a} vs {c.state_b}
  Description: {c.description}
  Winner: {c.winner or 'UNDETERMINED'}
  Evidence: {c.winner_evidence or 'PENDING'}
"""
        else:
            report += "  No active contradictions.\n"

        report += """
TRANSITION TRIGGERS:
"""
        if tz.level in [TransitionLevel.HIGH, TransitionLevel.CRITICAL]:
            report += """  [!] HIGH ALERT: Transition Zone elevated
      - Monitor: VIX, credit spreads, safe asset flows
      - If VIX > 25: DELEVERAGING_PRESSURE likely activates
      - If Gold down + VIX up: Liquidation cascade imminent
"""
        else:
            report += """  [ ] STANDARD MONITORING
      - No immediate transition triggers
      - Watch for contradiction resolution
"""

        report += f"""
================================================================================
ENGINE METADATA
================================================================================
Engine: State Conflict + Resolution Engine v1.0
Data Sources: Neo4j (state graph), Supabase (quant validation)
Snapshot Date: {date}
States Analyzed: {len(active_states)}
Contradictions Found: {len(contradictions)}
Transition Zone Level: {tz.level.value}
Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    engine = ConflictResolutionEngine()

    try:
        report = engine.generate_report(args.date)
        print(report)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\n✅ Saved to: {args.output}")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
