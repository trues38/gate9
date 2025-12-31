#!/usr/bin/env python3
"""
경제 이벤트 파이프라인 헬스 체크
일일 운영 통계 및 이상 징후 감지
"""

from neo4j import GraphDatabase
from datetime import datetime, timedelta
import json

NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "regime2025"

class PipelineHealthCheck:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {}

    def close(self):
        self.driver.close()

    def get_daily_stats(self):
        """오늘 생성된 이벤트 통계"""
        with self.driver.session() as session:
            # 오늘의 이벤트 총 수
            result = session.run("""
                MATCH (e:Event)
                WHERE date(e.timestamp) = date()
                RETURN count(e) as today_count
            """)
            self.stats['today_events'] = result.single()['today_count']

            # Tier별 분포
            result = session.run("""
                MATCH (e:Event)
                WHERE date(e.timestamp) = date()
                RETURN e.source_tier as tier, count(*) as count
                ORDER BY tier
            """)
            self.stats['tier_distribution'] = {record['tier']: record['count'] for record in result}

            # 고신뢰도 이벤트 (>0.8)
            result = session.run("""
                MATCH (e:Event)
                WHERE date(e.timestamp) = date()
                  AND e.confidence > 0.8
                RETURN count(e) as high_conf_count
            """)
            self.stats['high_confidence_count'] = result.single()['high_conf_count']

            # 타입별 분포
            result = session.run("""
                MATCH (e:Event)
                WHERE date(e.timestamp) = date()
                RETURN e.type as type, count(*) as count
                ORDER BY count DESC
            """)
            self.stats['type_distribution'] = {record['type']: record['count'] for record in result}

    def get_weekly_trend(self):
        """최근 7일 트렌드"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)
                WHERE e.timestamp > datetime() - duration('P7D')
                WITH date(e.timestamp) as day, count(e) as count
                RETURN day, count
                ORDER BY day DESC
            """)

            weekly_counts = {}
            for record in result:
                day_str = record['day'].to_native().strftime('%Y-%m-%d')
                weekly_counts[day_str] = record['count']

            self.stats['weekly_counts'] = weekly_counts

    def get_factor_impact(self):
        """Factor별 영향 집계"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
                WHERE date(e.timestamp) = date()
                RETURN f.name as factor,
                       sum(CASE WHEN r.impact_direction = 'increase' THEN r.impact_magnitude ELSE -r.impact_magnitude END) as net_impact,
                       count(e) as event_count
                ORDER BY abs(net_impact) DESC
            """)

            factor_impacts = []
            for record in result:
                factor_impacts.append({
                    'factor': record['factor'],
                    'net_impact': record['net_impact'],
                    'event_count': record['event_count']
                })

            self.stats['factor_impacts'] = factor_impacts

    def detect_anomalies(self):
        """이상 징후 감지"""
        anomalies = []

        # 1. 오늘 이벤트 0개
        if self.stats['today_events'] == 0:
            anomalies.append({
                'severity': 'high',
                'message': '오늘 생성된 이벤트가 0개입니다. n8n 워크플로우가 실행 중인지 확인하세요.'
            })

        # 2. Tier 1 이벤트 부재 (중앙은행/정부는 정기적으로 발표)
        if self.stats['tier_distribution'].get(1, 0) == 0:
            anomalies.append({
                'severity': 'medium',
                'message': 'Tier 1 이벤트가 없습니다. 중앙은행 계정 화이트리스트를 확인하세요.'
            })

        # 3. 고신뢰도 이벤트 비율 너무 낮음 (<10%)
        if self.stats['today_events'] > 0:
            high_conf_ratio = self.stats['high_confidence_count'] / self.stats['today_events']
            if high_conf_ratio < 0.1:
                anomalies.append({
                    'severity': 'low',
                    'message': f'고신뢰도 이벤트 비율이 {high_conf_ratio*100:.1f}%로 낮습니다. Grok 프롬프트를 확인하세요.'
                })

        # 4. 주간 평균 대비 급감 (50% 이하)
        if self.stats['weekly_counts']:
            weekly_avg = sum(self.stats['weekly_counts'].values()) / len(self.stats['weekly_counts'])
            if self.stats['today_events'] < weekly_avg * 0.5 and weekly_avg > 5:
                anomalies.append({
                    'severity': 'medium',
                    'message': f'오늘 이벤트 수({self.stats["today_events"]})가 주간 평균({weekly_avg:.1f})의 50% 미만입니다.'
                })

        self.stats['anomalies'] = anomalies

    def print_report(self):
        """헬스 체크 리포트 출력"""
        today = datetime.now().strftime('%Y-%m-%d')

        print("\n" + "=" * 80)
        print(f"📅 {today} 경제 이벤트 파이프라인 헬스 체크")
        print("=" * 80)

        # 오늘의 통계
        print(f"\n✓ 오늘 생성된 이벤트: {self.stats['today_events']}개")

        if self.stats['today_events'] > 0:
            # Tier 분포
            print("\nTier별 분포:")
            for tier in sorted(self.stats['tier_distribution'].keys()):
                count = self.stats['tier_distribution'][tier]
                pct = (count / self.stats['today_events']) * 100
                tier_name = {1: 'Central Banks', 2: 'Media', 3: 'Analysts'}.get(tier, 'Unknown')
                print(f"  Tier {tier} ({tier_name}): {count}개 ({pct:.1f}%)")

            # 타입 분포
            print("\n이벤트 타입별:")
            for event_type, count in self.stats['type_distribution'].items():
                pct = (count / self.stats['today_events']) * 100
                print(f"  {event_type}: {count}개 ({pct:.1f}%)")

            # 고신뢰도
            high_conf_pct = (self.stats['high_confidence_count'] / self.stats['today_events']) * 100
            print(f"\n고신뢰도(>0.8): {self.stats['high_confidence_count']}개 ({high_conf_pct:.1f}%)")

            # Factor 영향
            if self.stats['factor_impacts']:
                print("\nFactor 영향 (오늘):")
                for impact in self.stats['factor_impacts']:
                    direction = "↑" if impact['net_impact'] > 0 else "↓"
                    print(f"  {impact['factor']}: {direction} {abs(impact['net_impact']):.2f} ({impact['event_count']}개 이벤트)")

        # 주간 트렌드
        if self.stats['weekly_counts']:
            print("\n최근 7일 트렌드:")
            for day in sorted(self.stats['weekly_counts'].keys(), reverse=True):
                count = self.stats['weekly_counts'][day]
                bar = "█" * min(count, 50)  # 최대 50칸
                print(f"  {day}: {bar} {count}")

        # 이상 징후
        if self.stats['anomalies']:
            print("\n" + "⚠" * 40)
            print("🚨 감지된 이상 징후:")
            for anomaly in self.stats['anomalies']:
                severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[anomaly['severity']]
                print(f"  {severity_icon} [{anomaly['severity'].upper()}] {anomaly['message']}")
        else:
            print("\n✅ 이상 징후 없음. 파이프라인이 정상 작동 중입니다.")

        print("\n" + "=" * 80)

    def export_json(self, filepath):
        """JSON 파일로 내보내기 (자동화/대시보드용)"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 통계를 JSON으로 저장: {filepath}")

def main():
    checker = PipelineHealthCheck()

    try:
        # 통계 수집
        checker.get_daily_stats()
        checker.get_weekly_trend()
        checker.get_factor_impact()
        checker.detect_anomalies()

        # 리포트 출력
        checker.print_report()

        # JSON 내보내기 (선택)
        json_path = f"/Users/js/g9/logs/pipeline_health_{datetime.now().strftime('%Y%m%d')}.json"
        checker.export_json(json_path)

    finally:
        checker.close()

if __name__ == "__main__":
    main()
