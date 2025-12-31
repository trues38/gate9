#!/usr/bin/env python3
"""
선수-팀 관계 생성 (PLAYS_FOR)
현재 Player.team 속성을 기반으로 명시적인 관계 생성
"""

from neo4j import GraphDatabase
import os


class PlayerTeamRelationshipCreator:
    def __init__(self):
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password123')
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_player_team_relationships(self):
        """선수-팀 PLAYS_FOR 관계 생성"""
        with self.driver.session() as session:
            # 기존 관계 확인
            existing = session.run("""
                MATCH (p:Player)-[r:PLAYS_FOR]->(t:Team)
                RETURN COUNT(r) as count
            """)
            existing_count = existing.single()['count']

            if existing_count > 0:
                print(f"⚠️  이미 {existing_count}개의 PLAYS_FOR 관계가 존재합니다")
                return existing_count

            # 새로운 관계 생성
            result = session.run("""
                MATCH (p:Player), (t:Team)
                WHERE p.team = t.abbr
                MERGE (p)-[r:PLAYS_FOR]->(t)
                RETURN COUNT(r) as created
            """)

            created = result.single()['created']
            return created

    def verify_relationships(self):
        """관계 검증"""
        with self.driver.session() as session:
            print()
            print("관계 검증:")
            print("-"*70)

            # 관계 개수
            result = session.run("""
                MATCH (p:Player)-[r:PLAYS_FOR]->(t:Team)
                RETURN COUNT(r) as total_relations
            """)
            total = result.single()['total_relations']
            print(f"총 PLAYS_FOR 관계: {total}개")

            # 팀별 선수 수
            result = session.run("""
                MATCH (t:Team)<-[r:PLAYS_FOR]-(p:Player)
                WITH t.abbr as team_abbr, COUNT(p) as player_count
                ORDER BY player_count DESC
                RETURN team_abbr, player_count
            """)

            print()
            print("팀별 선수 수:")
            print("-"*70)
            for record in result:
                print(f"  {record['team_abbr']}: {record['player_count']:3d}명")

            # 관계 없는 선수 확인
            result = session.run("""
                MATCH (p:Player)
                WHERE NOT (p)-[:PLAYS_FOR]->(:Team)
                RETURN COUNT(p) as orphan_count, COUNT(DISTINCT p.team) as unique_teams
            """)

            orphan = result.single()
            if orphan['orphan_count'] > 0:
                print()
                print(f"⚠️  관계 없는 선수: {orphan['orphan_count']}명")
                print(f"   (팀 abbr: {orphan['unique_teams']}개)")

    def create_relationship_statistics(self):
        """선수-팀 관계 통계 노드 생성"""
        with self.driver.session() as session:
            print()
            print("선수-팀 관계 통계 생성:")
            print("-"*70)

            result = session.run("""
                MATCH (t:Team)<-[r:PLAYS_FOR]-(p:Player)
                WITH t, COUNT(p) as player_count,
                     AVG(p.ppg) as avg_ppg,
                     AVG(p.rpg) as avg_rpg,
                     AVG(p.apg) as avg_apg,
                     AVG(p.avg_plus_minus) as avg_pm
                MERGE (t)-[:HAS_ROSTER_STATS]->(rs:RosterStats {team: t.abbr})
                SET rs.total_players = player_count,
                    rs.avg_ppg = ROUND(avg_ppg, 2),
                    rs.avg_rpg = ROUND(avg_rpg, 2),
                    rs.avg_apg = ROUND(avg_apg, 2),
                    rs.avg_plus_minus = ROUND(avg_pm, 2),
                    rs.updated_at = datetime()
                RETURN t.name, player_count,
                       ROUND(avg_ppg, 2) as avg_ppg
            """)

            for record in result:
                print(f"  {record['t.name']:20} {record['player_count']:3d}명, 평균 PPG: {record['avg_ppg']}")


def main():
    creator = PlayerTeamRelationshipCreator()

    try:
        print("="*70)
        print("선수-팀 관계 생성")
        print("="*70)
        print()

        created = creator.create_player_team_relationships()

        if created > 0:
            print(f"✅ {created}개의 PLAYS_FOR 관계 생성 완료")
        else:
            print(f"✅ 관계 이미 존재")

        creator.verify_relationships()
        creator.create_relationship_statistics()

        print()
        print("="*70)
        print("✅ 완료!")
        print("="*70)

    finally:
        creator.close()


if __name__ == "__main__":
    main()
