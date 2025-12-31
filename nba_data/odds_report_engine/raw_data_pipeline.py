#!/usr/bin/env python3
"""
RAW 데이터 저장 파이프라인
================================================

목표: 6개월 후 "이 State가 돈이 되는가?"를 계산할 수 있게 데이터를 쌓는다

핵심:
1. RAW Event 저장
2. BoxScore 저장
3. State 스냅샷 저장
4. 날짜/경기 ID 고정
================================================
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from neo4j import GraphDatabase


class RawDataPipeline:
    """RAW 데이터 저장 파이프라인 (JSON + Neo4j 이중 백업)"""

    def __init__(
        self,
        base_dir="/Users/js/g9/nba_data/raw_events",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="quickpass123"
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Neo4j 연결
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            print("✅ Neo4j 연결 성공")
        except Exception as e:
            print(f"⚠️ Neo4j 연결 실패: {e}")
            self.driver = None

    def close(self):
        """Neo4j 연결 종료"""
        if self.driver:
            self.driver.close()

    # ========================================
    # 1. Event 저장
    # ========================================

    def save_event(self, event_data: Dict) -> str:
        """
        Event 저장 (JSON + Neo4j)

        Event는 경기 전 가설.
        검증 후 State를 업데이트하는 입력값으로만 사용.
        의사결정에 직접 재사용하지 않음.
        """
        # JSON 저장
        game_date = event_data['game_date']
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "events"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{event_data['event_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Event 저장 (JSON): {file_path}")

        # Neo4j 저장
        if self.driver:
            with self.driver.session() as session:
                session.run("""
                    MERGE (g:Game {game_id: $game_id})
                    CREATE (e:Event {
                      event_id: $event_id,
                      game_id: $game_id,
                      game_date: date($game_date),
                      created_at: datetime($created_at),
                      event_type: $event_type,
                      prediction: $prediction,
                      context: $context,
                      validated: false,
                      json_file_path: $json_file_path
                    })
                    CREATE (e)-[:EXPECTED_FOR {created_at: datetime($created_at)}]->(g)
                """,
                    event_id=event_data['event_id'],
                    game_id=event_data['game_id'],
                    game_date=event_data['game_date'],
                    created_at=event_data['created_at'],
                    event_type=event_data['event_type'],
                    prediction=json.dumps(event_data['prediction']),
                    context=json.dumps(event_data.get('context', {})),
                    json_file_path=str(file_path)
                )
                print(f"✅ Event 저장 (Neo4j): {event_data['event_id']}")

        return str(file_path)

    # ========================================
    # 2. AI Council Prediction 저장
    # ========================================

    def save_prediction(self, prediction_data: Dict) -> str:
        """AI Council Prediction 저장"""
        # JSON 저장
        game_date = prediction_data['game_date']
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "predictions"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{prediction_data['prediction_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(prediction_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Prediction 저장 (JSON): {file_path}")

        # Neo4j 저장
        if self.driver:
            with self.driver.session() as session:
                session.run("""
                    MERGE (g:Game {game_id: $game_id})
                    CREATE (c:CouncilPrediction {
                      prediction_id: $prediction_id,
                      game_id: $game_id,
                      game_date: date($game_date),
                      created_at: datetime($created_at),
                      consensus_score: $consensus_score,
                      recommendation: $recommendation,
                      confidence: $confidence,
                      individual_votes: $individual_votes,
                      was_correct: null,
                      json_file_path: $json_file_path
                    })
                    CREATE (c)-[:PREDICTED_FOR {created_at: datetime($created_at)}]->(g)
                """,
                    prediction_id=prediction_data['prediction_id'],
                    game_id=prediction_data['game_id'],
                    game_date=prediction_data['game_date'],
                    created_at=prediction_data['created_at'],
                    consensus_score=prediction_data['consensus']['score'],
                    recommendation=prediction_data['consensus']['recommendation'],
                    confidence=prediction_data['consensus']['confidence'],
                    individual_votes=json.dumps(prediction_data['individual_votes']),
                    json_file_path=str(file_path)
                )
                print(f"✅ Prediction 저장 (Neo4j): {prediction_data['prediction_id']}")

        return str(file_path)

    # ========================================
    # 3. BoxScore 저장 (정답지)
    # ========================================

    def save_boxscore(self, boxscore_data: Dict) -> str:
        """
        BoxScore 저장 (정답지)

        Event를 채점하고 State를 업데이트하는 기준
        """
        # JSON 저장
        game_date = boxscore_data['game_date']
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "boxscores"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{boxscore_data['boxscore_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(boxscore_data, f, indent=2, ensure_ascii=False)

        print(f"✅ BoxScore 저장 (JSON): {file_path}")

        # Neo4j 저장
        if self.driver:
            with self.driver.session() as session:
                session.run("""
                    MERGE (g:Game {game_id: $game_id})
                    CREATE (b:BoxScore {
                      boxscore_id: $boxscore_id,
                      game_id: $game_id,
                      game_date: date($game_date),
                      created_at: datetime($created_at),
                      home_score: $home_score,
                      away_score: $away_score,
                      margin: $margin,
                      spread_line: $spread_line,
                      spread_covered: $spread_covered,
                      measured_impacts: $measured_impacts,
                      json_file_path: $json_file_path
                    })
                    CREATE (g)-[:RESULTED_IN {completed_at: datetime($created_at)}]->(b)
                """,
                    boxscore_id=boxscore_data['boxscore_id'],
                    game_id=boxscore_data['game_id'],
                    game_date=boxscore_data['game_date'],
                    created_at=boxscore_data['created_at'],
                    home_score=boxscore_data['final_score']['home'],
                    away_score=boxscore_data['final_score']['away'],
                    margin=boxscore_data['final_score']['margin'],
                    spread_line=boxscore_data['spread_result']['line'],
                    spread_covered=boxscore_data['spread_result']['covered_by'],
                    measured_impacts=json.dumps(boxscore_data['measured_impacts']),
                    json_file_path=str(file_path)
                )
                print(f"✅ BoxScore 저장 (Neo4j): {boxscore_data['boxscore_id']}")

        return str(file_path)

    # ========================================
    # 4. Event Validation 저장 (채점 결과)
    # ========================================

    def save_validation(self, validation_data: Dict) -> str:
        """Event Validation 저장 (채점 결과)"""
        # game_date 추출 (event_id 또는 현재 날짜 사용)
        game_date = validation_data.get('game_date', datetime.now().strftime('%Y-%m-%d'))
        year_month = game_date[:7]

        save_dir = self.base_dir / year_month / game_date / "validations"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{validation_data['validation_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(validation_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Validation 저장 (JSON): {file_path}")

        # Neo4j에 VALIDATED 관계 생성
        if self.driver:
            with self.driver.session() as session:
                session.run("""
                    MATCH (e:Event {event_id: $event_id})
                    MATCH (b:BoxScore {game_id: $game_id})
                    CREATE (e)-[:VALIDATED {
                      validation_id: $validation_id,
                      success: $success,
                      impact_score: $impact_score,
                      comparison: $comparison,
                      validated_at: datetime($validated_at),
                      json_file_path: $json_file_path
                    }]->(b)
                    SET e.validated = true
                """,
                    validation_id=validation_data['validation_id'],
                    event_id=validation_data['event_id'],
                    game_id=validation_data['game_id'],
                    success=validation_data['result']['success'],
                    impact_score=validation_data['result']['impact_score'],
                    comparison=json.dumps(validation_data['result']['comparison']),
                    validated_at=validation_data['validated_at'],
                    json_file_path=str(file_path)
                )
                print(f"✅ Validation 저장 (Neo4j): {validation_data['validation_id']}")

        return str(file_path)

    # ========================================
    # 5. State Snapshot 저장 (업데이트된 상태)
    # ========================================

    def save_state_snapshot(self, state_data: Dict) -> str:
        """
        State Snapshot 저장 (업데이트된 상태)

        이게 진짜 학습된 결과.
        다음 경기에서 이것만 조회한다.
        """
        # JSON 저장
        snapshot_date = state_data['snapshot_date']
        year_month = snapshot_date[:7]

        save_dir = self.base_dir / year_month / snapshot_date / "states"
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{state_data['snapshot_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        print(f"✅ State Snapshot 저장 (JSON): {file_path}")

        # Neo4j 업데이트 (TeamState 노드)
        if self.driver:
            with self.driver.session() as session:
                session.run("""
                    MERGE (ts:TeamState {team_id: $team_id})
                    SET ts.current_regime = $regime_type,
                        ts.regime_confidence = $regime_confidence,
                        ts.regime_success_rate = $regime_success_rate,
                        ts.injury_resilience = $injury_resilience,
                        ts.injury_impact_history = $injury_impact_history,
                        ts.market_trust = $market_trust,
                        ts.market_accuracy = $market_accuracy,
                        ts.recent_form = $recent_form,
                        ts.avg_margin = $avg_margin,
                        ts.total_events_validated = $total_events_validated,
                        ts.successful_predictions = $successful_predictions,
                        ts.updated_at = datetime($updated_at),
                        ts.last_snapshot_file = $json_file_path

                    WITH ts
                    MATCH (b:BoxScore {game_id: $triggered_by_game})
                    CREATE (b)-[:UPDATED_STATE {
                      snapshot_id: $snapshot_id,
                      changes: $changes,
                      updated_at: datetime($updated_at)
                    }]->(ts)
                """,
                    snapshot_id=state_data['snapshot_id'],
                    team_id=state_data['team_id'],
                    regime_type=state_data['state']['regime']['type'],
                    regime_confidence=state_data['state']['regime']['confidence'],
                    regime_success_rate=state_data['state']['regime']['success_rate'],
                    injury_resilience=state_data['state']['injury_resilience']['level'],
                    injury_impact_history=state_data['state']['injury_resilience']['impact_history'],
                    market_trust=state_data['state']['market_trust']['level'],
                    market_accuracy=state_data['state']['market_trust']['accuracy'],
                    recent_form=state_data['state']['performance']['recent_form'],
                    avg_margin=state_data['state']['performance']['avg_margin'],
                    total_events_validated=state_data['state']['learning_metadata']['total_events_validated'],
                    successful_predictions=state_data['state']['learning_metadata']['successful_predictions'],
                    updated_at=state_data['created_at'],
                    triggered_by_game=state_data['triggered_by_game'],
                    changes=json.dumps(state_data.get('changes_from_previous', {})),
                    json_file_path=str(file_path)
                )
                print(f"✅ State Snapshot 저장 (Neo4j): {state_data['snapshot_id']}")

        return str(file_path)


# ========================================
# 사용 예시
# ========================================

def example_usage():
    """실제 사용 예시"""

    pipeline = RawDataPipeline()

    print("\n" + "=" * 70)
    print("🏀 RAW 데이터 저장 파이프라인 테스트")
    print("=" * 70)

    # 1. Event 저장
    print("\n[1] Event 저장...")
    event = {
        "event_id": "evt_20251228_401810212_injury_001",
        "game_id": "401810212",
        "game_date": "2025-12-28",
        "created_at": "2025-12-28T09:00:00Z",
        "event_type": "INJURY_IMPACT",
        "prediction": {
            "player": "RJ Barrett",
            "team": "TOR",
            "status": "OUT",
            "expected_impact": -8.5,
            "confidence": 0.75,
            "reasoning": "RJ Barrett OUT (21.5ppg, 주력 선수)"
        },
        "context": {
            "odds_at_creation": {
                "moneyline": {"GSW": -175, "TOR": 155},
                "spread": {"GSW": -4.5}
            }
        }
    }
    pipeline.save_event(event)

    # 2. AI Council Prediction 저장
    print("\n[2] AI Council Prediction 저장...")
    prediction = {
        "prediction_id": "pred_20251228_401810212",
        "game_id": "401810212",
        "game_date": "2025-12-28",
        "created_at": "2025-12-28T09:30:00Z",
        "consensus": {
            "score": "3/5",
            "recommendation": "BET",
            "confidence": "MEDIUM"
        },
        "individual_votes": [
            {
                "analyst": "DeepSeek V3.2",
                "vote": "BET",
                "confidence": "HIGH",
                "reasoning": "Regime 우위 명확"
            }
        ]
    }
    pipeline.save_prediction(prediction)

    # 3. BoxScore 저장 (경기 후)
    print("\n[3] BoxScore 저장...")
    boxscore = {
        "boxscore_id": "box_20251228_401810212",
        "game_id": "401810212",
        "game_date": "2025-12-28",
        "created_at": "2025-12-28T23:30:00Z",
        "final_score": {
            "home": 102,
            "away": 115,
            "margin": -13
        },
        "spread_result": {
            "line": -4.5,
            "covered_by": "AWAY",
            "margin_vs_spread": -8.5
        },
        "measured_impacts": {
            "home_injuries_impact": -12.3,
            "away_injuries_impact": -3.1
        }
    }
    pipeline.save_boxscore(boxscore)

    # 4. Event Validation 저장
    print("\n[4] Event Validation 저장...")
    validation = {
        "validation_id": "val_20251228_401810212_evt_001",
        "event_id": "evt_20251228_401810212_injury_001",
        "game_id": "401810212",
        "game_date": "2025-12-28",
        "validated_at": "2025-12-28T23:45:00Z",
        "result": {
            "success": True,
            "impact_score": 0.82,
            "comparison": {
                "expected": -8.5,
                "actual": -12.3,
                "error": 3.8
            }
        }
    }
    pipeline.save_validation(validation)

    # 5. State Snapshot 저장
    print("\n[5] State Snapshot 저장...")
    state = {
        "snapshot_id": "state_20251228_TOR_after_401810212",
        "team_id": "TOR",
        "snapshot_date": "2025-12-28",
        "triggered_by_game": "401810212",
        "created_at": "2025-12-28T23:50:00Z",
        "state": {
            "regime": {
                "type": "DECLINE",
                "confidence": 0.87,
                "success_rate": 0.73,
                "games_in_regime": 13
            },
            "injury_resilience": {
                "level": "LOW",
                "impact_history": [0.82, 0.9, 0.7],
                "avg_recovery": 0.81
            },
            "market_trust": {
                "level": "MEDIUM",
                "accuracy": 0.62,
                "last_30_games": 0.65
            },
            "performance": {
                "recent_form": "3-8",
                "avg_margin": -5.3,
                "home_record": "8-13"
            },
            "learning_metadata": {
                "total_events_validated": 46,
                "successful_predictions": 29,
                "overall_accuracy": 0.630
            }
        },
        "changes_from_previous": {
            "regime_confidence": +0.02,
            "injury_resilience": "MEDIUM → LOW"
        }
    }
    pipeline.save_state_snapshot(state)

    pipeline.close()

    print("\n" + "=" * 70)
    print("✅ 모든 데이터 저장 완료!")
    print("=" * 70)
    print("\n📁 저장 위치: /Users/js/g9/nba_data/raw_events/2025-12/2025-12-28/")
    print("💾 이중 백업: JSON 파일 + Neo4j")
    print("\n🎯 6개월 후 분석 가능: 'python3 analyze_historical_states.py'")


if __name__ == "__main__":
    example_usage()
