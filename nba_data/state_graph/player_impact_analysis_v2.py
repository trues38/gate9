#!/usr/bin/env python3
"""
선수 IN/OUT 영향 분석 v2.0
실제 출전 데이터 기반 (PlayerBoxScore 활용)

정성적 가설을 정량적으로 검증:
- Adams의 스크린 작업 → HOU 오펜스 효율
- 센터 부상 → 실제 수치 변화
"""

import json
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from collections import defaultdict

class PlayerImpactAnalyzerV2:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_player_games(self, team: str, player_name: str, season="2025-26") -> Dict:
        """
        선수가 출전한 경기 vs 결장한 경기 분석
        실제 PlayerBoxScore 데이터 기반
        """

        query_with = """
        MATCH (g:GameState)-[:HAS_BOXSCORE]->(pb:PlayerBoxScore)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND pb.team = $team
          AND pb.player_name CONTAINS $player_name
          AND g.date >= date('2025-10-01')
        WITH g, pb,
             CASE WHEN g.home_team = $team THEN g.home_win ELSE NOT g.home_win END AS win,
             CASE WHEN g.home_team = $team THEN g.home_score ELSE g.away_score END AS team_score,
             CASE WHEN g.home_team = $team THEN g.away_score ELSE g.home_score END AS opp_score
        RETURN count(*) AS games,
               sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins,
               round(avg(team_score), 1) AS avg_score,
               round(avg(opp_score), 1) AS avg_allowed,
               round(avg(team_score - opp_score), 1) AS avg_margin,
               avg(pb.minutes) AS avg_minutes,
               avg(pb.points) AS avg_pts,
               avg(pb.rebounds) AS avg_reb,
               avg(pb.off_rebounds) AS avg_oreb
        """

        query_without = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date('2025-10-01')
          AND NOT EXISTS {
              MATCH (g)-[:HAS_BOXSCORE]->(pb:PlayerBoxScore)
              WHERE pb.team = $team
                AND pb.player_name CONTAINS $player_name
          }
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_win ELSE NOT g.home_win END AS win,
             CASE WHEN g.home_team = $team THEN g.home_score ELSE g.away_score END AS team_score,
             CASE WHEN g.home_team = $team THEN g.away_score ELSE g.home_score END AS opp_score
        RETURN count(*) AS games,
               sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins,
               round(avg(team_score), 1) AS avg_score,
               round(avg(opp_score), 1) AS avg_allowed,
               round(avg(team_score - opp_score), 1) AS avg_margin
        """

        with self.driver.session() as session:
            with_player = session.run(query_with, team=team, player_name=player_name).single()
            without_player = session.run(query_without, team=team, player_name=player_name).single()

            return {
                'with_player': dict(with_player) if with_player and with_player['games'] > 0 else None,
                'without_player': dict(without_player) if without_player and without_player['games'] > 0 else None
            }

    def analyze_player_impact(self, team: str, player_name: str):
        """선수 영향 분석 (v2.0 - 실제 출전 기반)"""

        print("=" * 80)
        print(f"선수 영향 분석 v2.0: {team} - {player_name}")
        print("=" * 80)
        print(f"분석 방법: 실제 출전 데이터 기반 (PlayerBoxScore)")
        print(f"시즌: 2025-26 (Oct-Dec)")
        print()

        result = self.get_player_games(team, player_name)

        with_p = result['with_player']
        without = result['without_player']

        if not with_p:
            print(f"⚠️  {player_name} 출전 기록 없음")
            return

        print("-" * 80)
        print(f"📊 {player_name} 출전 시")
        print("-" * 80)
        print(f"  경기 수: {with_p['games']}경기")
        print(f"  전적: {with_p['wins']}승 {with_p['games']-with_p['wins']}패 ({with_p['wins']/with_p['games']*100:.1f}%)")
        print(f"  평균 득점: {with_p['avg_score']}점")
        print(f"  평균 실점: {with_p['avg_allowed']}점")
        print(f"  평균 득실차: {with_p['avg_margin']:+.1f}점")
        print()
        print(f"  {player_name} 개인 평균:")
        print(f"    출전시간: {with_p['avg_minutes']:.1f}분")
        print(f"    득점: {with_p['avg_pts']:.1f}점")
        print(f"    리바운드: {with_p['avg_reb']:.1f}개")
        if with_p['avg_oreb'] is not None:
            print(f"    오펜스 리바운드: {with_p['avg_oreb']:.1f}개")
        print()

        if not without:
            print("-" * 80)
            print(f"📊 {player_name} 결장 시")
            print("-" * 80)
            print(f"  ✅ 결장 경기 없음 - {player_name}가 모든 경기 출전!")
            print()
        else:
            print("-" * 80)
            print(f"📊 {player_name} 결장 시")
            print("-" * 80)
            print(f"  경기 수: {without['games']}경기")
            print(f"  전적: {without['wins']}승 {without['games']-without['wins']}패 ({without['wins']/without['games']*100:.1f}%)")
            print(f"  평균 득점: {without['avg_score']}점")
            print(f"  평균 실점: {without['avg_allowed']}점")
            print(f"  평균 득실차: {without['avg_margin']:+.1f}점")
            print()

            print("-" * 80)
            print(f"🔍 {player_name} 효과")
            print("-" * 80)

            win_pct_diff = (with_p['wins']/with_p['games'] - without['wins']/without['games']) * 100
            score_diff = with_p['avg_score'] - without['avg_score']
            allowed_diff = with_p['avg_allowed'] - without['avg_allowed']
            margin_diff = with_p['avg_margin'] - without['avg_margin']

            print(f"  승률 변화: {win_pct_diff:+.1f}%p")
            print(f"  득점 변화: {score_diff:+.1f}점")
            print(f"  실점 변화: {allowed_diff:+.1f}점")
            print(f"  득실차 변화: {margin_diff:+.1f}점")
            print()

            print("-" * 80)
            print("💡 해석")
            print("-" * 80)

            if abs(win_pct_diff) < 5:
                print(f"  • 승률 변화 미미 ({win_pct_diff:+.1f}%p)")
            elif win_pct_diff > 0:
                print(f"  • 승률 {win_pct_diff:+.1f}%p 상승 - {player_name} 긍정적 영향 ✅")
            else:
                print(f"  • 승률 {win_pct_diff:+.1f}%p 하락 - 다른 요인 가능성 ⚠️")

            if score_diff > 3:
                print(f"  • 공격력 {score_diff:+.1f}점 증가 - 오펜스 기여 명확 🔥")
            elif score_diff < -3:
                print(f"  • 공격력 {score_diff:+.1f}점 감소 - 오펜스 약화")

            if allowed_diff < -3:
                print(f"  • 수비력 {abs(allowed_diff):.1f}점 개선 - 수비 기여 명확 🛡️")
            elif allowed_diff > 3:
                print(f"  • 수비력 {allowed_diff:+.1f}점 악화")

            if with_p['avg_oreb'] and with_p['avg_oreb'] > 2.0:
                print(f"  • 오펜스 리바운드 {with_p['avg_oreb']:.1f}개/경기 - 세컨드 찬스 기여 💪")

            print()

        print("-" * 80)
        print("✅ 장점")
        print("-" * 80)
        print(f"  • 실제 출전 여부 기반 분석 (날짜 proxy 없음)")
        print(f"  • 선수 개인 스탯 포함 (출전시간, 득점, 리바운드)")
        print(f"  • 25-26 시즌 현재 로스터 기준")
        print()

        if without and without['games'] < 5:
            print("-" * 80)
            print("⚠️  주의사항")
            print("-" * 80)
            print(f"  • 결장 경기가 {without['games']}경기로 적음 (통계적 신뢰도 낮음)")
            print(f"  • 더 많은 데이터 필요")
            print()

def main():
    analyzer = PlayerImpactAnalyzerV2()

    try:
        # 분석 1: HOU - Adams
        print("분석 1: 휴스턴 - Steven Adams")
        analyzer.analyze_player_impact("HOU", "Adams")

        print("\n" + "=" * 80 + "\n")

        # 분석 2: BOS - Tatum (항상 출전하는 에이스)
        print("분석 2: 보스턴 - Jayson Tatum")
        analyzer.analyze_player_impact("BOS", "Tatum")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
