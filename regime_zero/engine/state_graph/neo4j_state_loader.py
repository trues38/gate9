#!/usr/bin/env python3
"""
Neo4j State Graph Loader
=========================
State Machine 결과를 Neo4j에 저장

이건 예측 DB가 아니다.
이건 상태 공간 그래프 DB다.
"""

import os
import json
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️ neo4j 미설치: pip install neo4j")


class Neo4jStateLoader:
    """Neo4j State Graph Loader"""

    def __init__(self):
        self.uri = os.getenv("NEO4J_ECONOMY_URI", "bolt://localhost:7688")
        self.user = os.getenv("NEO4J_ECONOMY_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_ECONOMY_PASSWORD", "regime2025")
        self.driver = None

    def connect(self) -> bool:
        """Neo4j 연결"""
        if not NEO4J_AVAILABLE:
            return False

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 연결 테스트
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            print(f"✅ Neo4j 연결: {self.uri}")
            return True
        except Exception as e:
            print(f"❌ Neo4j 연결 실패: {e}")
            return False

    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()

    def create_schema(self):
        """State Graph 스키마 생성"""
        with self.driver.session() as session:
            # Constraints
            session.run("""
                CREATE CONSTRAINT state_node_id IF NOT EXISTS
                FOR (s:StateNode) REQUIRE s.id IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT snapshot_id IF NOT EXISTS
                FOR (snap:StateSnapshot) REQUIRE snap.id IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT signal_id IF NOT EXISTS
                FOR (sig:ObservedSignal) REQUIRE sig.id IS UNIQUE
            """)
            print("✅ Schema 생성 완료")

    def create_state_ontology(self):
        """State Ontology 노드 생성 (최초 1회)"""

        # state_ontology.py에서 import
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from state_ontology import STATE_ONTOLOGY

        with self.driver.session() as session:
            for state_id, state in STATE_ONTOLOGY.items():
                session.run("""
                    MERGE (s:StateNode {id: $state_id})
                    SET s.drivers = $drivers,
                        s.signals = $signals,
                        s.interactions = $interactions,
                        s.blocked = $blocked
                """, {
                    "state_id": state_id,
                    "drivers": state.activation_drivers,
                    "signals": state.observable_signals,
                    "interactions": list(state.interaction_states),
                    "blocked": list(state.blocked_states),
                })

            # State 간 Interaction 관계 생성
            for state_id, state in STATE_ONTOLOGY.items():
                for interact_id in state.interaction_states:
                    session.run("""
                        MATCH (s1:StateNode {id: $state_id})
                        MATCH (s2:StateNode {id: $interact_id})
                        MERGE (s1)-[:CAN_INTERACT_WITH]->(s2)
                    """, {"state_id": state_id, "interact_id": interact_id})

                for blocked_id in state.blocked_states:
                    session.run("""
                        MATCH (s1:StateNode {id: $state_id})
                        MATCH (s2:StateNode {id: $blocked_id})
                        MERGE (s1)-[:BLOCKS]->(s2)
                    """, {"state_id": state_id, "blocked_id": blocked_id})

            print(f"✅ State Ontology 로드: {len(STATE_ONTOLOGY)}개 State")

    def load_daily_snapshot(self, result: Dict):
        """Daily State Snapshot 저장"""

        date = result["date"]
        snapshot_id = f"snapshot_{date}"

        with self.driver.session() as session:
            # 1. Snapshot 노드 생성
            session.run("""
                MERGE (snap:StateSnapshot {id: $snapshot_id})
                SET snap.date = $date,
                    snap.timestamp = datetime(),
                    snap.liquidity_pressure = $liq,
                    snap.policy_credibility = $pol,
                    snap.risk_appetite = $risk,
                    snap.correlation_stability = $corr
            """, {
                "snapshot_id": snapshot_id,
                "date": date,
                "liq": result["observation_summary"]["imbalances"]["liquidity"],
                "pol": result["observation_summary"]["imbalances"]["policy_credibility"],
                "risk": result["observation_summary"]["imbalances"]["risk_appetite"],
                "corr": result["observation_summary"]["imbalances"]["correlation_stability"],
            })

            # 2. Active States 연결
            for state in result["active_states"]:
                session.run("""
                    MATCH (snap:StateSnapshot {id: $snapshot_id})
                    MATCH (s:StateNode {id: $state_id})
                    MERGE (snap)-[r:ACTIVATED {level: $level, confidence: $conf}]->(s)
                    SET r.drivers = $drivers
                """, {
                    "snapshot_id": snapshot_id,
                    "state_id": state["state"],
                    "level": state["level"],
                    "conf": state["confidence"],
                    "drivers": state["drivers"],
                })

            # 3. Observed Signals 생성 및 연결
            for signal in result["observation_summary"]["active_signals"]:
                signal_id = f"signal_{date}_{signal}"
                session.run("""
                    MERGE (sig:ObservedSignal {id: $signal_id})
                    SET sig.name = $signal,
                        sig.date = $date

                    WITH sig
                    MATCH (snap:StateSnapshot {id: $snapshot_id})
                    MERGE (snap)-[:OBSERVED]->(sig)
                """, {
                    "signal_id": signal_id,
                    "signal": signal,
                    "date": date,
                    "snapshot_id": snapshot_id,
                })

            # 4. Open Transitions 연결
            for transition in result["open_transition_windows"]:
                session.run("""
                    MATCH (snap:StateSnapshot {id: $snapshot_id})
                    MATCH (s:StateNode {id: $state_id})
                    MERGE (snap)-[:TRANSITION_OPEN]->(s)
                """, {
                    "snapshot_id": snapshot_id,
                    "state_id": transition,
                })

            # 5. 이전 Snapshot과 시계열 연결
            session.run("""
                MATCH (current:StateSnapshot {id: $snapshot_id})
                MATCH (prev:StateSnapshot)
                WHERE prev.date < $date
                WITH prev ORDER BY prev.date DESC LIMIT 1
                MATCH (current:StateSnapshot {id: $snapshot_id})
                MERGE (prev)-[:NEXT_DAY]->(current)
            """, {
                "snapshot_id": snapshot_id,
                "date": date,
            })

            print(f"  ✅ {date} Snapshot 저장")

    def load_december_data(self):
        """12월 전체 State Graph 로드"""

        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from state_machine_engine import StateMachineEngine

        ECON_FILE = os.path.join(BASE_DIR, "data/raw_econ_archive.jsonl")

        # 12월 데이터 로드
        december_data = []
        with open(ECON_FILE, 'r') as f:
            for line in f:
                r = json.loads(line)
                date = r.get('date', '')
                if date.startswith('2025-12'):
                    december_data.append({
                        "date": date,
                        "econ_data": r.get('econ_data', {})
                    })

        print(f"\n📊 12월 데이터: {len(december_data)}일")

        # State Machine Engine 초기화
        engine = StateMachineEngine()

        # 각 날짜별 처리 및 저장
        for day in sorted(december_data, key=lambda x: x['date']):
            result = engine.process(day['econ_data'], day['date'])
            self.load_daily_snapshot(result)

        print(f"\n✅ 12월 전체 로드 완료: {len(december_data)}일")

    def query_state_path(self, start_date: str, end_date: str) -> List[Dict]:
        """특정 기간의 State 경로 쿼리"""

        with self.driver.session() as session:
            result = session.run("""
                MATCH (snap:StateSnapshot)-[a:ACTIVATED]->(s:StateNode)
                WHERE snap.date >= $start AND snap.date <= $end
                RETURN snap.date as date, s.id as state, a.level as level, a.confidence as conf
                ORDER BY snap.date, a.confidence DESC
            """, {"start": start_date, "end": end_date})

            return [dict(r) for r in result]

    def find_structural_twins(self, date: str) -> List[Dict]:
        """구조적 Twin 검색 (서브그래프 유사성)"""

        with self.driver.session() as session:
            # 현재 날짜의 활성 State 패턴
            result = session.run("""
                // 현재 날짜의 활성 State
                MATCH (current:StateSnapshot {date: $date})-[a:ACTIVATED]->(s:StateNode)
                WHERE a.level IN ['HIGH', 'PEAK', 'ELEVATED']
                WITH collect(s.id) as current_states

                // 과거 Snapshot에서 동일 패턴 검색
                MATCH (past:StateSnapshot)-[a2:ACTIVATED]->(s2:StateNode)
                WHERE past.date < $date
                  AND a2.level IN ['HIGH', 'PEAK', 'ELEVATED']
                  AND s2.id IN current_states

                WITH past, current_states,
                     collect(s2.id) as past_states,
                     count(s2) as match_count

                WHERE match_count >= 2

                RETURN past.date as twin_date,
                       past_states as matching_states,
                       match_count,
                       toFloat(match_count) / size(current_states) as similarity
                ORDER BY similarity DESC
                LIMIT 5
            """, {"date": date})

            return [dict(r) for r in result]


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["setup", "load", "query", "twin"],
                        default="load", help="실행할 작업")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    loader = Neo4jStateLoader()

    if not loader.connect():
        print("Neo4j 연결 실패. 종료.")
        return

    try:
        if args.action == "setup":
            # 최초 설정
            loader.create_schema()
            loader.create_state_ontology()

        elif args.action == "load":
            # 12월 데이터 로드
            loader.create_schema()
            loader.create_state_ontology()
            loader.load_december_data()

        elif args.action == "query":
            # 경로 쿼리
            results = loader.query_state_path("2025-12-01", args.date)
            print(f"\n📊 State Path ({len(results)} records):")
            for r in results[:20]:
                print(f"  {r['date']}: {r['state']} ({r['level']}, {r['conf']:.2f})")

        elif args.action == "twin":
            # 구조적 Twin 검색
            twins = loader.find_structural_twins(args.date)
            print(f"\n🔍 Structural Twins for {args.date}:")
            for t in twins:
                print(f"  {t['twin_date']}: {t['matching_states']} (sim: {t['similarity']:.2%})")

    finally:
        loader.close()


if __name__ == "__main__":
    main()
