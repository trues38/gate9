#!/usr/bin/env python3
"""
심판별 통계 생성 - 심판이 담당한 경기들의 기본 통계
"""

from neo4j import GraphDatabase
from datetime import datetime
import os


class RefereeStatsGenerator:
    def __init__(self):
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password123')
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def generate_referee_stats(self, referee_name):
        """심판의 기본 통계 생성"""
        with self.driver.session() as session:
            # 해당 심판이 담당한 경기 수만 조회
            result = session.run("""
                MATCH (r:Referee {name: $referee_name})<-[:OFFICIATED_BY]-(g:GameState)
                RETURN count(DISTINCT g) as total_games,
                       max(g.date) as most_recent_date
            """, referee_name=referee_name)

            stats = result.single()

            if stats['total_games'] < 5:
                return None

            return {
                'referee': referee_name,
                'total_games': stats['total_games'],
                'most_recent_date': stats['most_recent_date'],
                'updated_at': datetime.now().isoformat()
            }

    def save_referee_stats(self, stats_data):
        """Neo4j에 저장"""
        with self.driver.session() as session:
            session.run("""
                MATCH (r:Referee {name: $referee})
                MERGE (r)-[:HAS_STATS]->(rs:RefereeStats)
                SET rs.total_games = $total_games,
                    rs.most_recent_date = $most_recent_date,
                    rs.updated_at = $updated_at
            """,
                referee=stats_data['referee'],
                total_games=stats_data['total_games'],
                most_recent_date=stats_data['most_recent_date'],
                updated_at=stats_data['updated_at']
            )

    def generate_all(self):
        """모든 심판의 통계 생성"""
        with self.driver.session() as session:
            # 최소 5경기 이상 담당한 심판들
            result = session.run("""
                MATCH (r:Referee)<-[:OFFICIATED_BY]-(g:GameState)
                WITH r.name as referee, count(g) as games
                WHERE games >= 5
                RETURN referee
                ORDER BY referee
            """)

            referees = [r['referee'] for r in result]

        print(f"총 {len(referees)}명 심판 처리 시작")
        print("="*70)

        success_count = 0
        error_count = 0

        for i, referee in enumerate(referees, 1):
            try:
                print(f"[{i}/{len(referees)}] {referee:30}", end=' ')

                stats_data = self.generate_referee_stats(referee)
                if stats_data:
                    self.save_referee_stats(stats_data)
                    print("✅")
                    success_count += 1
                else:
                    print("⏭️  (데이터 부족)")

            except Exception as e:
                print(f"❌ {str(e)[:50]}")
                error_count += 1

        print()
        print("="*70)
        print(f"✅ 성공: {success_count}명")
        print(f"❌ 실패: {error_count}명")
        print(f"📊 생성된 RefereeStats 노드: {success_count}개")


def main():
    generator = RefereeStatsGenerator()

    try:
        print("="*70)
        print("RefereeStats 생성 시작")
        print("="*70)
        print()

        generator.generate_all()

        print()
        print("✅ 완료!")

    finally:
        generator.close()


if __name__ == "__main__":
    main()
