#!/usr/bin/env python3
"""
현재 Neo4j 데이터의 샘플 사이즈 분석
각 팀별 컨텍스트 조합의 경기 수를 확인
"""

from neo4j import GraphDatabase
from collections import defaultdict
import json

class SampleSizeAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def analyze_rest_day_samples(self):
        """팀별 휴식일 조합의 샘플 수"""
        query = """
        MATCH (g:GameState)
        WITH g.home_team AS team, g.home_rest_days AS rest, 'home' AS location,
             count(*) AS games,
             sum(CASE WHEN g.home_win THEN 1 ELSE 0 END) AS wins
        RETURN team, rest, location, games, wins
        UNION ALL
        MATCH (g:GameState)
        WITH g.away_team AS team, g.away_rest_days AS rest, 'away' AS location,
             count(*) AS games,
             sum(CASE WHEN NOT g.home_win THEN 1 ELSE 0 END) AS wins
        RETURN team, rest, location, games, wins
        ORDER BY games DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            records = list(result)

        # 분석
        stats = {
            'total_combinations': len(records),
            'by_sample_size': defaultdict(int),
            'insufficient_samples': [],  # < 10 games
            'good_samples': [],  # >= 10 games
            'excellent_samples': []  # >= 20 games
        }

        for record in records:
            team = record['team']
            rest = record['rest']
            location = record['location']
            games = record['games']
            wins = record['wins']

            if games > 0:
                win_pct = round(wins * 100.0 / games, 1)
            else:
                win_pct = 0

            item = {
                'team': team,
                'rest_days': rest,
                'location': location,
                'games': games,
                'win_pct': win_pct
            }

            # 샘플 크기별 분류
            if games >= 20:
                stats['excellent_samples'].append(item)
                stats['by_sample_size']['20+'] += 1
            elif games >= 10:
                stats['good_samples'].append(item)
                stats['by_sample_size']['10-19'] += 1
            elif games >= 5:
                stats['by_sample_size']['5-9'] += 1
                stats['insufficient_samples'].append(item)
            else:
                stats['by_sample_size']['<5'] += 1
                stats['insufficient_samples'].append(item)

        return stats

    def analyze_data_by_season(self):
        """시즌별 데이터 분포"""
        query = """
        MATCH (g:GameState)
        WITH substring(toString(g.date), 0, 4) AS year,
             count(*) AS games
        RETURN year, games
        ORDER BY year DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            return list(result)

    def get_total_stats(self):
        """전체 통계"""
        query = """
        MATCH (g:GameState)
        RETURN count(*) AS total_games,
               count(DISTINCT g.home_team) AS total_teams,
               min(g.date) AS earliest_game,
               max(g.date) AS latest_game
        """

        with self.driver.session() as session:
            result = session.run(query)
            return result.single()

def main():
    analyzer = SampleSizeAnalyzer()

    try:
        print("=" * 80)
        print("Neo4j 데이터 샘플 사이즈 분석")
        print("=" * 80)

        # 전체 통계
        total = analyzer.get_total_stats()
        print(f"\n📊 전체 데이터:")
        print(f"   총 경기: {total['total_games']}개")
        print(f"   팀 수: {total['total_teams']}개")
        print(f"   기간: {total['earliest_game']} ~ {total['latest_game']}")

        # 시즌별 분포
        print(f"\n📅 시즌별 분포:")
        seasons = analyzer.analyze_data_by_season()
        for season in seasons:
            print(f"   {season['year']}년: {season['games']}경기")

        # 휴식일 패턴 샘플 분석
        print(f"\n🔍 휴식일 패턴 샘플 분석:")
        stats = analyzer.analyze_rest_day_samples()

        print(f"\n   총 팀×휴식일×장소 조합: {stats['total_combinations']}개")
        print(f"\n   샘플 크기 분포:")
        print(f"   • 20경기 이상 (우수): {stats['by_sample_size']['20+']}개")
        print(f"   • 10-19경기 (양호): {stats['by_sample_size']['10-19']}개")
        print(f"   • 5-9경기 (부족): {stats['by_sample_size']['5-9']}개")
        print(f"   • 5경기 미만 (매우 부족): {stats['by_sample_size']['<5']}개")

        print(f"\n⚠️  문제점:")
        insufficient_pct = (stats['by_sample_size']['5-9'] + stats['by_sample_size']['<5']) / stats['total_combinations'] * 100
        print(f"   전체 조합 중 {insufficient_pct:.1f}%가 샘플 부족 (<10경기)")
        print(f"   이런 패턴으로 예측하면 신뢰도가 매우 낮음")

        # 우수 샘플 예시
        print(f"\n✅ 신뢰할 수 있는 패턴 (20경기 이상):")
        for item in stats['excellent_samples'][:5]:
            print(f"   {item['team']} {item['location']} {item['rest_days']}일 휴식: "
                  f"{item['win_pct']}% ({item['games']}경기)")

        # 부족한 샘플 예시
        print(f"\n❌ 신뢰할 수 없는 패턴 (5경기 미만):")
        insufficient_under_5 = [x for x in stats['insufficient_samples'] if x['games'] < 5]
        for item in insufficient_under_5[:5]:
            print(f"   {item['team']} {item['location']} {item['rest_days']}일 휴식: "
                  f"{item['win_pct']}% ({item['games']}경기) ⚠️")

        print(f"\n" + "=" * 80)
        print(f"\n💡 결론:")
        print(f"   현재 927경기로는 샘플이 부족합니다.")
        print(f"   특히 특정 휴식일 조합은 경기 수가 너무 적어 신뢰도 낮음.")
        print(f"   권장: 최근 2시즌 (2,000+ 경기) 데이터 확보 필요")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
