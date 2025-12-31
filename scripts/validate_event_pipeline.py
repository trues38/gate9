#!/usr/bin/env python3
"""
경제 이벤트 파이프라인 검증 스크립트
n8n 워크플로우가 제대로 작동하는지 확인합니다.
"""

from neo4j import GraphDatabase
from datetime import datetime, timedelta
import sys

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "regime2025"

class EventPipelineValidator:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.results = {
            'connection': False,
            'events_found': 0,
            'affects_relationships': 0,
            'tier1_events_24h': 0,
            'high_confidence_events': 0,
            'avg_confidence': 0.0,
            'event_types': {},
            'issues': []
        }

    def close(self):
        self.driver.close()

    def test_connection(self):
        """Neo4j 연결 테스트"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                if result.single()['test'] == 1:
                    self.results['connection'] = True
                    return True
        except Exception as e:
            self.results['issues'].append(f"Neo4j 연결 실패: {e}")
            return False

    def check_events(self):
        """Event 노드 확인"""
        with self.driver.session() as session:
            # 전체 이벤트 수
            result = session.run("MATCH (e:Event) RETURN count(e) as count")
            self.results['events_found'] = result.single()['count']

            if self.results['events_found'] == 0:
                self.results['issues'].append("Event 노드가 없습니다. 워크플로우가 실행되었는지 확인하세요.")
                return

            # 이벤트 타입별 분포
            result = session.run("""
                MATCH (e:Event)
                RETURN e.type as type, count(*) as count
            """)
            for record in result:
                self.results['event_types'][record['type']] = record['count']

            # 평균 confidence
            result = session.run("""
                MATCH (e:Event)
                WHERE e.confidence IS NOT NULL
                RETURN avg(e.confidence) as avg_conf
            """)
            self.results['avg_confidence'] = result.single()['avg_conf'] or 0.0

            # 고신뢰도 이벤트 (>0.8)
            result = session.run("""
                MATCH (e:Event)
                WHERE e.confidence > 0.8
                RETURN count(e) as count
            """)
            self.results['high_confidence_events'] = result.single()['count']

    def check_relationships(self):
        """AFFECTS 관계 확인"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
                RETURN count(r) as count
            """)
            self.results['affects_relationships'] = result.single()['count']

            if self.results['affects_relationships'] == 0 and self.results['events_found'] > 0:
                self.results['issues'].append("Event는 있지만 AFFECTS 관계가 없습니다. Grok 분석이 Factor를 제대로 식별하지 못했을 수 있습니다.")

    def check_tier1_recent(self):
        """최근 24시간 Tier 1 이벤트 확인"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)
                WHERE e.source_tier = 1
                  AND e.timestamp > datetime() - duration('P1D')
                RETURN count(e) as count
            """)
            self.results['tier1_events_24h'] = result.single()['count']

            if self.results['tier1_events_24h'] == 0:
                self.results['issues'].append("최근 24시간 Tier 1 이벤트가 없습니다. 중앙은행/정부 계정이 트윗하지 않았거나 필터링되었을 수 있습니다.")

    def print_report(self):
        """검증 리포트 출력"""
        print("\n" + "=" * 80)
        print("경제 이벤트 파이프라인 검증 리포트")
        print("=" * 80)
        print(f"검증 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 연결 상태
        if self.results['connection']:
            print("✓ Neo4j 연결 성공")
        else:
            print("✗ Neo4j 연결 실패")
            for issue in self.results['issues']:
                print(f"  - {issue}")
            return

        # Event 노드
        print(f"✓ Event 노드: {self.results['events_found']}개 발견")

        if self.results['events_found'] > 0:
            # 이벤트 타입별
            print("\n이벤트 타입별 분포:")
            for event_type, count in self.results['event_types'].items():
                print(f"  - {event_type}: {count}개")

            # 신뢰도
            print(f"\n평균 Confidence: {self.results['avg_confidence']:.2f}")
            print(f"고신뢰도 이벤트(>0.8): {self.results['high_confidence_events']}개")

            # 관계
            print(f"\n✓ AFFECTS 관계: {self.results['affects_relationships']}개 생성")

            # Tier 1 최근 이벤트
            if self.results['tier1_events_24h'] > 0:
                print(f"✓ Tier 1 이벤트(24h): {self.results['tier1_events_24h']}개")
            else:
                print(f"⚠ Tier 1 이벤트(24h): 0개")

        # 이슈
        if self.results['issues']:
            print("\n" + "⚠" * 40)
            print("발견된 이슈:")
            for issue in self.results['issues']:
                print(f"  - {issue}")
        else:
            print("\n✅ 모든 검증 통과! 파이프라인이 정상 작동 중입니다.")

        print("\n" + "=" * 80)

    def sample_events(self):
        """샘플 이벤트 출력"""
        if self.results['events_found'] == 0:
            return

        print("\n최근 이벤트 샘플 (최대 5개):")
        print("-" * 80)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)
                OPTIONAL MATCH (e)-[r:AFFECTS]->(f:InfluenceFactor)
                RETURN e.title as title,
                       e.type as type,
                       e.confidence as confidence,
                       e.source_tier as tier,
                       e.timestamp as timestamp,
                       collect(f.name) as factors
                ORDER BY e.timestamp DESC
                LIMIT 5
            """)

            for i, record in enumerate(result, 1):
                timestamp = record['timestamp'].to_native() if record['timestamp'] else 'N/A'
                factors = ', '.join(record['factors']) if record['factors'] else 'None'

                print(f"\n{i}. {record['title']}")
                print(f"   Type: {record['type']} | Tier: {record['tier']} | Confidence: {record['confidence']:.2f}")
                print(f"   Factors: {factors}")
                print(f"   Time: {timestamp}")

def main():
    validator = EventPipelineValidator()

    try:
        # 검증 실행
        validator.test_connection()

        if validator.results['connection']:
            validator.check_events()
            validator.check_relationships()
            validator.check_tier1_recent()

        # 리포트 출력
        validator.print_report()
        validator.sample_events()

        # 종료 코드
        if validator.results['issues']:
            sys.exit(1)  # 이슈 있음
        else:
            sys.exit(0)  # 정상

    finally:
        validator.close()

if __name__ == "__main__":
    main()
