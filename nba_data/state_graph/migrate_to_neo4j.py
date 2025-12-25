"""
Neo4j 마이그레이션 스크립트
===========================
tactics_seed.json 데이터를 Neo4j로 임포트

Made with ❤️ by State Graph Engine
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
from neo4j import GraphDatabase
from pathlib import Path


# ============================================================================
# Neo4j 연결
# ============================================================================

class Neo4jMigration:
    """Neo4j 마이그레이션 클래스"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password123"):
        """
        Args:
            uri: Neo4j 연결 URI
            user: 사용자명
            password: 비밀번호
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ Neo4j 연결 성공: {uri}")

    def close(self):
        """연결 종료"""
        self.driver.close()

    # ========================================================================
    # Step 1: Constraints & Indexes
    # ========================================================================

    def create_constraints_and_indexes(self):
        """Constraints와 Indexes 생성"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 1: Constraints & Indexes 생성")
            print("=" * 70)

            # Constraints
            constraints = [
                "CREATE CONSTRAINT team_abbr IF NOT EXISTS FOR (t:Team) REQUIRE t.abbr IS UNIQUE",
                "CREATE CONSTRAINT player_name IF NOT EXISTS FOR (p:Player) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT referee_name IF NOT EXISTS FOR (r:Referee) REQUIRE r.name IS UNIQUE",
                "CREATE CONSTRAINT tactic_name IF NOT EXISTS FOR (t:Tactic) REQUIRE t.name IS UNIQUE",
                "CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:GameState) REQUIRE g.game_id IS UNIQUE"
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✅ {constraint.split()[2]}")
                except Exception as e:
                    print(f"⚠️  {constraint.split()[2]}: {e}")

            # Indexes
            indexes = [
                "CREATE INDEX game_date IF NOT EXISTS FOR (g:GameState) ON (g.date)",
                "CREATE INDEX tactic_category IF NOT EXISTS FOR (t:Tactic) ON (t.category)"
            ]

            for index in indexes:
                try:
                    session.run(index)
                    print(f"✅ {index.split()[2]}")
                except Exception as e:
                    print(f"⚠️  {index.split()[2]}: {e}")

    # ========================================================================
    # Step 2: 전술 노드 생성
    # ========================================================================

    def create_tactics(self, tactics_data: List[Dict]):
        """전술 노드 생성"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 2: 전술 노드 생성")
            print("=" * 70)

            # tactics_data에서 고유한 전술 추출
            unique_tactics = {}
            for tag in tactics_data:
                tactic_name = tag['tactic_name']
                if tactic_name not in unique_tactics:
                    unique_tactics[tactic_name] = {
                        'name': tactic_name,
                        'category': tag['category'],
                        'usage_count': 0,
                        'total_confidence': 0.0
                    }
                unique_tactics[tactic_name]['usage_count'] += 1
                unique_tactics[tactic_name]['total_confidence'] += tag['confidence']

            # Neo4j에 생성
            for tactic_name, tactic_info in unique_tactics.items():
                avg_confidence = tactic_info['total_confidence'] / tactic_info['usage_count']

                session.run("""
                    MERGE (t:Tactic {name: $name})
                    SET t.category = $category,
                        t.effectiveness = $effectiveness,
                        t.usage_count = $usage_count,
                        t.origin_team = $origin_team
                """,
                    name=tactic_name,
                    category=tactic_info['category'],
                    effectiveness=round(avg_confidence, 2),
                    usage_count=tactic_info['usage_count'],
                    origin_team="Unknown"  # 나중에 수동 입력
                )

                print(f"✅ {tactic_name} ({tactic_info['category']}, "
                      f"effectiveness: {avg_confidence:.2f})")

    # ========================================================================
    # Step 3: 팀 노드 생성
    # ========================================================================

    def create_teams(self, tactics_data: List[Dict]):
        """팀 노드 생성"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 3: 팀 노드 생성")
            print("=" * 70)

            # 고유한 팀 추출
            unique_teams = set(tag['team'] for tag in tactics_data)

            for team_abbr in unique_teams:
                session.run("""
                    MERGE (t:Team {abbr: $abbr})
                    SET t.name = $name,
                        t.conference = $conference,
                        t.division = $division
                """,
                    abbr=team_abbr,
                    name=team_abbr,  # 나중에 풀네임으로 교체
                    conference="Unknown",
                    division="Unknown"
                )

                print(f"✅ {team_abbr}")

    # ========================================================================
    # Step 4: GameState 노드 생성
    # ========================================================================

    def create_game_states(self, games_data: List[Dict], tactics_data: List[Dict]):
        """GameState 노드 생성"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 4: GameState 노드 생성")
            print("=" * 70)

            # 게임별로 그룹화
            games_map = {game['game_id']: game for game in games_data}

            for game_id, game_info in games_map.items():
                # 이 게임의 전술 태그들
                game_tactics = [t for t in tactics_data if t['game_id'] == game_id]

                if not game_tactics:
                    continue

                # GameState 노드 생성
                session.run("""
                    CREATE (g:GameState {
                        game_id: $game_id,
                        date: date($date),
                        matchup: $matchup,
                        home_team: $home_team,
                        away_team: $away_team
                    })
                """,
                    game_id=game_id,
                    date=game_info['date'],
                    matchup=game_info['matchup'],
                    home_team=game_info['matchup'].split(' @ ')[1],  # "ORL @ MIA" → MIA
                    away_team=game_info['matchup'].split(' @ ')[0]   # "ORL @ MIA" → ORL
                )

                print(f"✅ {game_id}: {game_info['matchup']} ({game_info['date']})")

    # ========================================================================
    # Step 5: 관계 생성
    # ========================================================================

    def create_relationships(self, tactics_data: List[Dict]):
        """전술 관계 생성"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 5: 관계 생성 (USES_TACTIC)")
            print("=" * 70)

            for tag in tactics_data:
                # Team → Tactic
                session.run("""
                    MATCH (team:Team {abbr: $team})
                    MATCH (tactic:Tactic {name: $tactic})

                    MERGE (team)-[u:USES_TACTIC]->(tactic)
                    ON CREATE SET u.first_seen = date($date),
                                  u.usage_count = 1,
                                  u.avg_confidence = $confidence
                    ON MATCH SET u.usage_count = u.usage_count + 1,
                                 u.avg_confidence = (u.avg_confidence * (u.usage_count - 1) + $confidence) / u.usage_count
                """,
                    team=tag['team'],
                    tactic=tag['tactic_name'],
                    date=tag['date'],
                    confidence=tag['confidence']
                )

                # GameState → Tactic
                session.run("""
                    MATCH (game:GameState {game_id: $game_id})
                    MATCH (tactic:Tactic {name: $tactic})

                    CREATE (game)-[:FEATURED_TACTIC {
                        team: $team,
                        confidence: $confidence
                    }]->(tactic)
                """,
                    game_id=tag['game_id'],
                    tactic=tag['tactic_name'],
                    team=tag['team'],
                    confidence=tag['confidence']
                )

            print(f"✅ {len(tactics_data)}개 관계 생성 완료")

    # ========================================================================
    # Step 6: 수동 전술 상성 입력 (샘플)
    # ========================================================================

    def create_sample_counters(self):
        """샘플 전술 상성 관계"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("Step 6: 샘플 전술 상성 생성")
            print("=" * 70)

            # 수동 입력 (도메인 지식 기반)
            counters = [
                {
                    'counter': 'No-Pick Roll Play',
                    'target': 'Gap Defense',
                    'win_rate': 0.72,
                    'avg_point_diff': 8.5,
                    'sample_size': 8,
                    'mechanism': '갭 디펜스의 스크린 예상을 역이용'
                },
                {
                    'counter': 'Pace & Space',
                    'target': 'Inside Spacing',
                    'win_rate': 0.65,
                    'avg_point_diff': 5.2,
                    'sample_size': 5,
                    'mechanism': '빠른 템포로 인사이드 장악 무력화'
                }
            ]

            for counter_info in counters:
                try:
                    session.run("""
                        MATCH (counter:Tactic {name: $counter})
                        MATCH (target:Tactic {name: $target})

                        MERGE (counter)-[c:COUNTERS]->(target)
                        SET c.win_rate = $win_rate,
                            c.avg_point_diff = $avg_point_diff,
                            c.sample_size = $sample_size,
                            c.mechanism = $mechanism,
                            c.source = 'manual_expert_input'
                    """,
                        counter=counter_info['counter'],
                        target=counter_info['target'],
                        win_rate=counter_info['win_rate'],
                        avg_point_diff=counter_info['avg_point_diff'],
                        sample_size=counter_info['sample_size'],
                        mechanism=counter_info['mechanism']
                    )

                    print(f"✅ {counter_info['counter']} → {counter_info['target']} "
                          f"({counter_info['win_rate']} 승률)")
                except Exception as e:
                    print(f"⚠️  {counter_info['counter']} → {counter_info['target']}: {e}")

    # ========================================================================
    # 통합 실행
    # ========================================================================

    def run_migration(self, seed_file: str = "tactics_seed.json"):
        """전체 마이그레이션 실행"""

        print("=" * 70)
        print("Neo4j 마이그레이션 시작")
        print("=" * 70)

        # 데이터 로드
        with open(seed_file, 'r', encoding='utf-8') as f:
            seed_data = json.load(f)

        tactics_data = seed_data['tactic_tags']
        games_data = seed_data['games']

        print(f"\n로드된 데이터:")
        print(f"  - 경기 수: {len(games_data)}개")
        print(f"  - 전술 태그: {len(tactics_data)}개")

        # 순차 실행
        try:
            self.create_constraints_and_indexes()
            self.create_tactics(tactics_data)
            self.create_teams(tactics_data)
            self.create_game_states(games_data, tactics_data)
            self.create_relationships(tactics_data)
            self.create_sample_counters()

            print("\n" + "=" * 70)
            print("✅ 마이그레이션 완료!")
            print("=" * 70)

            # 통계
            self.print_stats()

        except Exception as e:
            print(f"\n❌ 마이그레이션 실패: {e}")
            raise

    def print_stats(self):
        """데이터베이스 통계"""

        with self.driver.session() as session:
            print("\n" + "=" * 70)
            print("데이터베이스 통계")
            print("=" * 70)

            # 노드 수
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            """)

            print("\n노드 수:")
            for record in result:
                print(f"  {record['label']}: {record['count']}개")

            # 관계 수
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """)

            print("\n관계 수:")
            for record in result:
                print(f"  {record['type']}: {record['count']}개")


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Neo4j 마이그레이션")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--user", default="neo4j", help="사용자명")
    parser.add_argument("--password", default="password123", help="비밀번호")
    parser.add_argument("--seed-file", default="tactics_seed.json", help="시드 데이터 파일")

    args = parser.parse_args()

    # 마이그레이션 실행
    migration = Neo4jMigration(
        uri=args.uri,
        user=args.user,
        password=args.password
    )

    try:
        migration.run_migration(args.seed_file)
    finally:
        migration.close()

    print("\n" + "=" * 70)
    print("다음 단계:")
    print("=" * 70)
    print("1. Neo4j Browser 열기: http://localhost:7474")
    print("2. 쿼리 실행: MATCH (n) RETURN n LIMIT 25")
    print("3. Graph Viewer 쿼리 테스트:")
    print("   - docs/GRAPH_VIEWER_QUERIES.cypher 참고")
    print("=" * 70)
