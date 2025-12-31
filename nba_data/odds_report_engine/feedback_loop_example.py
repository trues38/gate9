#!/usr/bin/env python3
"""
NBA GraphRAG Feedback Loop - 실제 사용 예시
================================================

핵심 개념:
1. Event는 버린다 (검증만 함)
2. State만 조회한다 (다음 경기 예측용)
3. BoxScore로 채점하고 State를 업데이트한다

================================================
"""

from neo4j import GraphDatabase
from datetime import datetime
from typing import Dict, List


class FeedbackLoopManager:
    """NBA GraphRAG Feedback Loop Manager"""

    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="quickpass123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ========================================
    # 경기 전: Event 생성 (일회용)
    # ========================================

    def create_injury_event(self, game_id: str, team_id: str, expected_impact: float) -> Dict:
        """
        경기 전 Injury Event 생성

        이 Event는 경기 후 검증되고 버려진다.
        대신 검증 결과는 TeamState.injury_resilience에 반영된다.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (g:Game {game_id: $game_id})
                CREATE (e:Event {
                  event_id: randomUUID(),
                  game_id: $game_id,
                  created_at: datetime(),
                  event_type: 'INJURY_IMPACT',
                  prediction: {
                    expected_impact: $expected_impact,
                    confidence: 0.75,
                    reasoning: "RJ Barrett OUT (21.5ppg)"
                  },
                  validated: false
                })
                CREATE (e)-[:EXPECTED_FOR {created_at: datetime()}]->(g)
                RETURN e.event_id AS event_id
            """, game_id=game_id, expected_impact=expected_impact)

            event_id = result.single()["event_id"]
            print(f"✅ Injury Event 생성: {event_id}")
            print(f"   예상 영향: {expected_impact} points")
            return {"event_id": event_id, "expected_impact": expected_impact}

    def create_ai_council_prediction(self, game_id: str, consensus: Dict) -> Dict:
        """AI Council 예측 저장"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (g:Game {game_id: $game_id})
                CREATE (c:CouncilPrediction {
                  game_id: $game_id,
                  created_at: datetime(),
                  consensus_score: $consensus_score,
                  recommendation: $recommendation,
                  confidence: $confidence,
                  deepseek_vote: $deepseek_vote,
                  qwen_vote: $qwen_vote,
                  grok_vote: $grok_vote,
                  gemini_vote: $gemini_vote,
                  gpt_vote: $gpt_vote,
                  was_correct: null
                })
                CREATE (c)-[:PREDICTED_FOR {created_at: datetime()}]->(g)
                RETURN c.game_id AS game_id
            """,
                game_id=game_id,
                consensus_score=consensus['score'],
                recommendation=consensus['recommendation'],
                confidence=consensus['confidence'],
                deepseek_vote=consensus['votes']['deepseek'],
                qwen_vote=consensus['votes']['qwen'],
                grok_vote=consensus['votes']['grok'],
                gemini_vote=consensus['votes']['gemini'],
                gpt_vote=consensus['votes']['gpt']
            )

            print(f"✅ AI Council 예측 저장: {consensus['score']} ({consensus['recommendation']})")
            return {"game_id": game_id}

    # ========================================
    # 경기 후: BoxScore 수집 및 검증
    # ========================================

    def collect_boxscore(self, game_id: str, home_score: int, away_score: int,
                         spread_line: float, injuries_impact: float) -> Dict:
        """
        경기 후 BoxScore 수집 및 저장

        이게 "정답지"다.
        """
        with self.driver.session() as session:
            result = session.run("""
                MERGE (g:Game {game_id: $game_id})
                CREATE (b:BoxScore {
                  game_id: $game_id,
                  created_at: datetime(),
                  home_score: $home_score,
                  away_score: $away_score,
                  margin: $margin,
                  spread_line: $spread_line,
                  spread_covered: CASE
                    WHEN $margin + $spread_line > 0 THEN 'HOME'
                    ELSE 'AWAY'
                  END,
                  home_injuries_impact: $injuries_impact
                })
                CREATE (g)-[:RESULTED_IN {completed_at: datetime()}]->(b)
                RETURN b.margin AS margin, b.spread_covered AS covered
            """,
                game_id=game_id,
                home_score=home_score,
                away_score=away_score,
                margin=home_score - away_score,
                spread_line=spread_line,
                injuries_impact=injuries_impact
            )

            record = result.single()
            print(f"✅ BoxScore 저장: {home_score} - {away_score} (Margin: {record['margin']})")
            print(f"   Spread Covered: {record['covered']}")
            return {"margin": record["margin"], "covered": record["covered"]}

    def validate_events(self, game_id: str) -> Dict:
        """
        Event 검증 (채점)

        예측 vs 실제를 비교하고 성공/실패 판정
        """
        with self.driver.session() as session:
            # Injury Event 검증
            result = session.run("""
                MATCH (e:Event {game_id: $game_id, event_type: 'INJURY_IMPACT'})-[:EXPECTED_FOR]->(g:Game)
                MATCH (g)-[:RESULTED_IN]->(b:BoxScore)
                WITH e, b,
                     e.prediction.expected_impact AS expected,
                     b.home_injuries_impact AS actual,
                     abs(b.home_injuries_impact - e.prediction.expected_impact) AS error
                CREATE (e)-[:VALIDATED {
                  success: CASE WHEN error < 5.0 THEN true ELSE false END,
                  impact_score: 1.0 - (error / 20.0),
                  actual_vs_expected: actual,
                  error_margin: error,
                  validated_at: datetime()
                }]->(b)
                SET e.validated = true
                RETURN e.event_id AS event_id,
                       expected,
                       actual,
                       error,
                       CASE WHEN error < 5.0 THEN 'SUCCESS' ELSE 'FAILED' END AS result
            """, game_id=game_id)

            validation_results = []
            for record in result:
                validation_results.append({
                    "event_id": record["event_id"],
                    "expected": record["expected"],
                    "actual": record["actual"],
                    "error": record["error"],
                    "result": record["result"]
                })
                print(f"✅ Event 검증: {record['result']}")
                print(f"   예측: {record['expected']}, 실제: {record['actual']}, 오차: {record['error']:.1f}")

            return {"validated_events": validation_results}

    def update_team_state(self, game_id: str, team_id: str) -> Dict:
        """
        Team State 업데이트 (핵심!)

        Event 검증 결과를 바탕으로 State를 업데이트한다.
        이게 "오답 노트" 작성이다.
        """
        with self.driver.session() as session:
            # Regime Confidence 업데이트
            result = session.run("""
                MATCH (e:Event {game_id: $game_id})-[v:VALIDATED]->(b:BoxScore)
                MATCH (g:Game {game_id: $game_id})
                MATCH (ts:TeamState {team_id: $team_id})
                WITH ts, b,
                     count(e) AS total_events,
                     sum(CASE WHEN v.success = true THEN 1 ELSE 0 END) AS successful_events,
                     toFloat(sum(CASE WHEN v.success = true THEN 1 ELSE 0 END)) / count(e) AS success_rate
                SET ts.regime_success_rate =
                      (COALESCE(ts.regime_success_rate, 0.5) * 0.9) + (success_rate * 0.1),
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
                  reason: total_events + ' events validated',
                  updated_at: datetime()
                }]->(ts)
                RETURN ts.team_id AS team_id,
                       ts.regime_confidence AS new_confidence,
                       ts.regime_success_rate AS new_success_rate
            """, game_id=game_id, team_id=team_id)

            record = result.single()
            if record:
                print(f"✅ Team State 업데이트: {record['team_id']}")
                print(f"   Regime Confidence: {record['new_confidence']:.2f}")
                print(f"   Success Rate: {record['new_success_rate']:.2%}")
                return {
                    "team_id": record["team_id"],
                    "regime_confidence": record["new_confidence"],
                    "success_rate": record["new_success_rate"]
                }

            return {}

    # ========================================
    # 다음 경기: State 조회 (Event 조회 안 함!)
    # ========================================

    def get_team_state_for_analysis(self, team_id: str) -> Dict:
        """
        다음 경기 분석용 Team State 조회

        중요: Event를 조회하지 않는다!
        State만 조회한다. (학습된 결과만 사용)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ts:TeamState {team_id: $team_id})
                RETURN {
                  team_id: ts.team_id,

                  // Regime (학습된 값)
                  current_regime: ts.current_regime,
                  regime_confidence: ts.regime_confidence,
                  regime_success_rate: ts.regime_success_rate,

                  // Injury Resilience (학습된 값)
                  injury_resilience: ts.injury_resilience,
                  injury_impact_history: ts.injury_impact_history,

                  // Market Trust (학습된 값)
                  market_trust: ts.market_trust,
                  market_accuracy: ts.market_accuracy,

                  // Performance
                  recent_form: ts.recent_form,
                  avg_margin: ts.avg_margin,

                  // Metadata
                  total_events_validated: ts.total_events_validated,
                  successful_predictions: ts.successful_predictions,
                  updated_at: ts.updated_at
                } AS team_state
            """, team_id=team_id)

            record = result.single()
            if record:
                state = record["team_state"]
                print(f"\n📊 Team State: {state['team_id']}")
                print(f"   Regime: {state['current_regime']} ({state['regime_confidence']:.2%} conf)")
                print(f"   Regime Success Rate: {state.get('regime_success_rate', 0):.2%}")
                print(f"   Injury Resilience: {state.get('injury_resilience', 'N/A')}")
                print(f"   Market Trust: {state.get('market_trust', 'N/A')}")
                print(f"   Total Events Validated: {state.get('total_events_validated', 0)}")
                return state

            return {}


# ============================================================
# 실제 사용 예시
# ============================================================

def example_full_cycle():
    """
    완전한 피드백 루프 예시:
    1. 경기 전: Event 생성 + AI 예측
    2. 경기 후: BoxScore 수집 + Event 검증 + State 업데이트
    3. 다음 경기: State 조회 (더 정확한 예측)
    """

    manager = FeedbackLoopManager()

    print("=" * 70)
    print("🏀 NBA GraphRAG Feedback Loop - Full Cycle Example")
    print("=" * 70)

    # ========================================
    # Day 1: 경기 전 (TOR vs GSW)
    # ========================================
    print("\n[Day 1 - 경기 전] TOR vs GSW")
    print("-" * 70)

    game_id = "401810212"

    # 1. Event 생성 (RJ Barrett OUT)
    manager.create_injury_event(
        game_id=game_id,
        team_id="TOR",
        expected_impact=-8.5  # 예상: 8.5점 손실
    )

    # 2. AI Council 예측 저장
    manager.create_ai_council_prediction(
        game_id=game_id,
        consensus={
            "score": "3/5",
            "recommendation": "BET",
            "confidence": "MEDIUM",
            "votes": {
                "deepseek": "BET",
                "qwen": "BET",
                "grok": "PASS",
                "gemini": "BET",
                "gpt": "PASS"
            }
        }
    )

    # ========================================
    # Day 1: 경기 후
    # ========================================
    print("\n[Day 1 - 경기 후] BoxScore 수집")
    print("-" * 70)

    # 3. BoxScore 수집 (실제 결과)
    manager.collect_boxscore(
        game_id=game_id,
        home_score=102,
        away_score=115,
        spread_line=-4.5,
        injuries_impact=-12.3  # 실제: 12.3점 손실
    )

    # 4. Event 검증 (채점)
    manager.validate_events(game_id=game_id)

    # 5. State 업데이트 (학습)
    manager.update_team_state(game_id=game_id, team_id="TOR")

    # ========================================
    # Day 2: 다음 경기 분석 (TOR vs BOS)
    # ========================================
    print("\n[Day 2 - 다음 경기] TOR vs BOS")
    print("-" * 70)

    # 6. 업데이트된 State 조회 (Event 조회 안 함!)
    tor_state = manager.get_team_state_for_analysis("TOR")

    print("\n🎯 분석:")
    print(f"   - Regime Confidence가 업데이트되었습니다 (학습됨)")
    print(f"   - Injury Resilience가 학습되었습니다")
    print(f"   - 이제 더 정확한 예측이 가능합니다!")

    manager.close()

    print("\n" + "=" * 70)
    print("✅ Feedback Loop 완료!")
    print("=" * 70)


def example_query_only():
    """State 조회만 하는 예시 (일반적인 사용)"""

    manager = FeedbackLoopManager()

    print("\n📊 Team State 조회 예시")
    print("-" * 70)

    # 다음 경기 분석용 State 조회
    tor_state = manager.get_team_state_for_analysis("TOR")
    gsw_state = manager.get_team_state_for_analysis("GSW")

    # AI Council에 전달
    context = {
        "home_team_state": tor_state,
        "away_team_state": gsw_state
    }

    print("\n✅ 이 State를 AI Council에 전달하여 예측합니다")
    print("   (Event는 조회하지 않습니다!)")

    manager.close()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("\n선택:")
    print("1. Full Cycle 예시 (경기 전 → 경기 후 → 다음 경기)")
    print("2. State 조회만 (일반적인 사용)")

    choice = input("\n선택 (1 or 2): ").strip()

    if choice == "1":
        example_full_cycle()
    elif choice == "2":
        example_query_only()
    else:
        print("❌ 잘못된 선택")


# ============================================================
# 핵심 원칙 요약
# ============================================================
#
# 1. Event는 일회용 (검증 후 Archive)
# 2. State는 누적 (계속 업데이트)
# 3. BoxScore는 채점기 (정답지)
# 4. 다음 경기는 State만 조회
# 5. 오답 노트 = State 업데이트 로직
#
# 이게 ML이다!
#
# ============================================================
