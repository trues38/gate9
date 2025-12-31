#!/usr/bin/env python3
"""
⚠️ DEPRECATED - 2025-12-30
==========================
이 파일은 더 이상 사용되지 않습니다.

대체: engine/unified_pipeline.py

문제:
- Supabase econ_daily 테이블 없음 (PGRST205 에러)
- Supabase는 web auth 전용으로 재정의됨

새 아키텍처:
  Yahoo Finance 단일 소스 → DVSS → State Engine
===========================

G9 Hybrid RAG Engine [LEGACY]
=====================
Supabase (Quant Layer) + Neo4j (State Graph + 20K Regimes)

This is the production engine for State Adjudication Bulletins.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Neo4j
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️ neo4j not installed")

# Supabase
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ supabase not installed")


@dataclass
class QuantSnapshot:
    """Daily quantitative snapshot from Supabase"""
    date: str
    vix: Optional[float] = None
    vix_change: Optional[float] = None
    spx: Optional[float] = None
    spx_change: Optional[float] = None
    gold: Optional[float] = None
    gold_change: Optional[float] = None
    dxy: Optional[float] = None
    dxy_change: Optional[float] = None
    btc: Optional[float] = None
    btc_change: Optional[float] = None
    oil: Optional[float] = None
    oil_change: Optional[float] = None
    treasury_20y: Optional[float] = None
    ig_spread: Optional[float] = None
    hy_spread: Optional[float] = None
    ted_spread: Optional[float] = None
    news_headlines: List[str] = None
    z_scores: Dict = None


@dataclass
class RegimeContext:
    """Historical regime context from Neo4j"""
    similar_regimes: List[Dict]
    transition_history: List[Dict]
    failure_patterns: List[Dict]
    interaction_graph: Dict


class HybridRAGEngine:
    """
    Hybrid RAG: Supabase Quant + Neo4j State Graph

    Query Flow:
    1. Get latest quant data from Supabase
    2. Get current state graph from Neo4j
    3. Search for similar historical regimes (20K archive)
    4. Combine for adjudication
    """

    def __init__(self):
        self.supabase = None
        self.neo4j = None
        self._connect()

    def _connect(self):
        """Connect to both data sources"""
        # Supabase
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
            if url and key:
                try:
                    self.supabase = create_client(url, key)
                    print("✅ Supabase connected")
                except Exception as e:
                    print(f"⚠️ Supabase failed: {e}")

        # Neo4j
        if NEO4J_AVAILABLE:
            uri = os.getenv("NEO4J_ECONOMY_URI", "bolt://localhost:7688")
            user = os.getenv("NEO4J_ECONOMY_USERNAME", "neo4j")
            password = os.getenv("NEO4J_ECONOMY_PASSWORD", "regime2025")
            try:
                self.neo4j = GraphDatabase.driver(uri, auth=(user, password))
                with self.neo4j.session() as session:
                    session.run("RETURN 1")
                print("✅ Neo4j connected")
            except Exception as e:
                print(f"⚠️ Neo4j failed: {e}")

    def close(self):
        if self.neo4j:
            self.neo4j.close()

    # =========================================
    # SUPABASE QUANT LAYER
    # =========================================

    def get_quant_snapshot(self, date: str) -> QuantSnapshot:
        """Get quantitative data from Supabase"""
        snapshot = QuantSnapshot(date=date, news_headlines=[], z_scores={})

        if not self.supabase:
            # Fallback to local file
            return self._get_quant_from_local(date)

        try:
            # Try econ_daily table
            result = self.supabase.table("econ_daily").select("*").eq("date", date).execute()
            if result.data:
                data = result.data[0]
                snapshot.vix = data.get("vix")
                snapshot.vix_change = data.get("vix_pct_change")
                snapshot.spx = data.get("spx")
                snapshot.spx_change = data.get("spx_pct_change")
                snapshot.gold = data.get("gold")
                snapshot.gold_change = data.get("gold_pct_change")
                snapshot.dxy = data.get("dxy")
                snapshot.btc = data.get("btc")
        except Exception as e:
            print(f"Supabase query failed: {e}")

        # Try news headlines
        try:
            result = self.supabase.table("news_headlines").select("headline").eq("date", date).limit(10).execute()
            if result.data:
                snapshot.news_headlines = [r["headline"] for r in result.data]
        except:
            pass

        # Try z-scores
        try:
            result = self.supabase.table("zscore_daily").select("*").eq("date", date).execute()
            if result.data:
                snapshot.z_scores = result.data[0]
        except:
            pass

        return snapshot

    def _get_quant_from_local(self, date: str) -> QuantSnapshot:
        """Fallback: get quant from local archive"""
        snapshot = QuantSnapshot(date=date, news_headlines=[], z_scores={})

        archive_path = os.path.join(BASE_DIR, "data/raw_econ_archive.jsonl")
        try:
            with open(archive_path, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("date") == date:
                        econ = record.get("econ_data", {})

                        # Parse nested structure
                        if "vix" in econ:
                            v = econ["vix"]
                            snapshot.vix = v.get("value") if isinstance(v, dict) else v
                            snapshot.vix_change = v.get("pct_change") if isinstance(v, dict) else None

                        if "gold" in econ:
                            g = econ["gold"]
                            snapshot.gold = g.get("value") if isinstance(g, dict) else g
                            snapshot.gold_change = g.get("pct_change") if isinstance(g, dict) else None

                        if "spx" in econ:
                            s = econ["spx"]
                            snapshot.spx = s.get("value") if isinstance(s, dict) else s
                            snapshot.spx_change = s.get("pct_change") if isinstance(s, dict) else None

                        if "dxy" in econ:
                            d = econ["dxy"]
                            snapshot.dxy = d.get("value") if isinstance(d, dict) else d

                        if "btc" in econ:
                            b = econ["btc"]
                            snapshot.btc = b.get("value") if isinstance(b, dict) else b
                            snapshot.btc_change = b.get("pct_change") if isinstance(b, dict) else None

                        break
        except Exception as e:
            print(f"Local archive read failed: {e}")

        return snapshot

    # =========================================
    # NEO4J STATE GRAPH LAYER
    # =========================================

    def get_current_state_graph(self, date: str) -> Dict:
        """Get current state graph from Neo4j"""
        if not self.neo4j:
            return {"error": "Neo4j not connected"}

        with self.neo4j.session() as session:
            # Active states
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                RETURN s.id as state, a.level as level, a.confidence as intensity, a.drivers as mechanisms
                ORDER BY a.confidence DESC
            """, {"date": date})
            active_states = [dict(r) for r in result]

            # Interactions
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

            # Open transitions
            result = session.run("""
                MATCH (snap:StateSnapshot {date: $date})-[:TRANSITION_OPEN]->(s:StateNode)
                RETURN s.id as state
            """, {"date": date})
            open_transitions = [r["state"] for r in result]

        return {
            "date": date,
            "active_states": active_states,
            "interactions": interactions,
            "open_transitions": open_transitions,
        }

    def search_similar_regimes(self, date: str, limit: int = 10) -> List[Dict]:
        """Search for similar historical regimes"""
        if not self.neo4j:
            return []

        with self.neo4j.session() as session:
            result = session.run("""
                // Get current pattern
                MATCH (current:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE a.level IN ["HIGH", "PEAK", "ELEVATED"]
                WITH collect(s.id) as current_states

                // Find similar past patterns
                MATCH (past:StateSnapshot)-[a2:ACTIVATED]->(s2:StateNode)
                WHERE past.date < $date
                  AND a2.level IN ["HIGH", "PEAK", "ELEVATED"]
                  AND s2.id IN current_states

                WITH past, current_states,
                     collect(s2.id) as matching_states,
                     count(s2) as match_count

                WHERE match_count >= 2

                // Get outcome (next day states)
                OPTIONAL MATCH (past)-[:NEXT_DAY]->(next:StateSnapshot)-[na:ACTIVATED]->(ns:StateNode)
                WHERE na.level IN ["HIGH", "PEAK", "ELEVATED"]

                RETURN past.date as regime_date,
                       matching_states,
                       toFloat(match_count) / size(current_states) as similarity,
                       collect(DISTINCT ns.id) as outcome_states
                ORDER BY similarity DESC, past.date DESC
                LIMIT $limit
            """, {"date": date, "limit": limit})

            return [dict(r) for r in result]

    def get_transition_history(self, state_id: str, limit: int = 10) -> List[Dict]:
        """Get historical transitions from a specific state"""
        if not self.neo4j:
            return []

        with self.neo4j.session() as session:
            result = session.run("""
                MATCH (snap1:StateSnapshot)-[a1:ACTIVATED {level: "PEAK"}]->(s1:StateNode {id: $state_id})
                MATCH (snap1)-[:NEXT_DAY]->(snap2:StateSnapshot)-[a2:ACTIVATED]->(s2:StateNode)
                WHERE a2.level IN ["HIGH", "PEAK", "ELEVATED"]
                RETURN snap1.date as from_date, s1.id as from_state,
                       collect(DISTINCT s2.id) as to_states
                ORDER BY snap1.date DESC
                LIMIT $limit
            """, {"state_id": state_id, "limit": limit})

            return [dict(r) for r in result]

    # =========================================
    # HYBRID RAG QUERY
    # =========================================

    def query(self, date: str) -> Dict:
        """
        Main hybrid RAG query

        Returns combined context from both data sources
        """
        # 1. Get quant snapshot
        quant = self.get_quant_snapshot(date)

        # 2. Get current state graph
        state_graph = self.get_current_state_graph(date)

        # 3. Search similar historical regimes
        similar_regimes = self.search_similar_regimes(date)

        # 4. Get transition history for peak states
        transition_history = []
        for state in state_graph.get("active_states", []):
            if state.get("level") == "PEAK":
                history = self.get_transition_history(state["state"])
                if history:
                    transition_history.extend(history)

        # 5. Detect quant-based signals
        quant_signals = self._detect_quant_signals(quant)

        # 6. Cross-validate state vs quant
        validation = self._cross_validate(state_graph, quant)

        return {
            "date": date,
            "quant_snapshot": {
                "vix": quant.vix,
                "vix_change": quant.vix_change,
                "spx": quant.spx,
                "spx_change": quant.spx_change,
                "gold": quant.gold,
                "gold_change": quant.gold_change,
                "dxy": quant.dxy,
                "btc": quant.btc,
                "btc_change": quant.btc_change,
                "headlines": quant.news_headlines[:5] if quant.news_headlines else [],
            },
            "state_graph": state_graph,
            "similar_regimes": similar_regimes,
            "transition_history": transition_history,
            "quant_signals": quant_signals,
            "cross_validation": validation,
        }

    def _detect_quant_signals(self, quant: QuantSnapshot) -> List[Dict]:
        """Detect signals from quant data"""
        signals = []

        # VIX stress
        if quant.vix and quant.vix > 25:
            signals.append({
                "signal": "VIX_STRESS",
                "value": quant.vix,
                "threshold": 25,
                "implication": "Elevated fear, possible deleveraging",
            })

        # VIX spike
        if quant.vix_change and quant.vix_change > 10:
            signals.append({
                "signal": "VIX_SPIKE",
                "value": quant.vix_change,
                "threshold": 10,
                "implication": "Sudden fear increase, volatility event",
            })

        # Gold liquidation
        if quant.gold_change and quant.gold_change < -2:
            signals.append({
                "signal": "GOLD_LIQUIDATION",
                "value": quant.gold_change,
                "threshold": -2,
                "implication": "Safe asset selling, liquidity stress",
            })

        # DXY strength
        if quant.dxy and quant.dxy > 105:
            signals.append({
                "signal": "DOLLAR_STRENGTH",
                "value": quant.dxy,
                "threshold": 105,
                "implication": "Dollar liquidity tightening",
            })

        # BTC weakness
        if quant.btc_change and quant.btc_change < -5:
            signals.append({
                "signal": "CRYPTO_STRESS",
                "value": quant.btc_change,
                "threshold": -5,
                "implication": "Risk asset selling, speculative retreat",
            })

        return signals

    def _cross_validate(self, state_graph: Dict, quant: QuantSnapshot) -> Dict:
        """Cross-validate state graph with quant data"""
        validations = []
        conflicts = []

        active_states = [s["state"] for s in state_graph.get("active_states", [])]

        # LIQUIDITY_STRESS should show gold weakness or VIX elevation
        if "LIQUIDITY_STRESS" in active_states:
            if quant.gold_change and quant.gold_change < -1:
                validations.append({
                    "state": "LIQUIDITY_STRESS",
                    "quant": f"Gold {quant.gold_change:.1f}%",
                    "status": "CONFIRMED",
                })
            elif quant.vix and quant.vix > 20:
                validations.append({
                    "state": "LIQUIDITY_STRESS",
                    "quant": f"VIX {quant.vix:.1f}",
                    "status": "CONFIRMED",
                })
            else:
                conflicts.append({
                    "state": "LIQUIDITY_STRESS",
                    "expected": "Gold weakness or VIX elevation",
                    "actual": f"Gold {quant.gold_change}, VIX {quant.vix}",
                    "status": "CONFLICT",
                })

        # CORRELATION_REGIME_BREAK harder to validate without correlation data
        if "CORRELATION_REGIME_BREAK" in active_states:
            validations.append({
                "state": "CORRELATION_REGIME_BREAK",
                "quant": "Requires correlation data (not in snapshot)",
                "status": "UNVALIDATED",
            })

        return {
            "validated": validations,
            "conflicts": conflicts,
            "validation_rate": len(validations) / max(len(active_states), 1),
        }


def main():
    """Demo: Run hybrid RAG query"""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    engine = HybridRAGEngine()

    try:
        result = engine.query(args.date)

        print(f"\n{'='*60}")
        print(f"HYBRID RAG QUERY: {args.date}")
        print(f"{'='*60}\n")

        print("QUANT SNAPSHOT:")
        for k, v in result["quant_snapshot"].items():
            if v is not None and v != []:
                print(f"  {k}: {v}")

        print(f"\nSTATE GRAPH:")
        print(f"  Active States: {len(result['state_graph']['active_states'])}")
        for s in result['state_graph']['active_states'][:5]:
            print(f"    - {s['state']}: {s['level']} ({s['intensity']:.2f})")

        print(f"\nSIMILAR REGIMES: {len(result['similar_regimes'])}")
        for r in result['similar_regimes'][:3]:
            print(f"  - {r['regime_date']}: {r['matching_states']} ({r['similarity']:.0%})")
            if r.get('outcome_states'):
                print(f"    → Outcome: {r['outcome_states']}")

        print(f"\nQUANT SIGNALS: {len(result['quant_signals'])}")
        for s in result['quant_signals']:
            print(f"  - {s['signal']}: {s['value']} (threshold: {s['threshold']})")

        print(f"\nCROSS-VALIDATION:")
        print(f"  Validated: {len(result['cross_validation']['validated'])}")
        print(f"  Conflicts: {len(result['cross_validation']['conflicts'])}")

    finally:
        engine.close()


if __name__ == "__main__":
    main()
