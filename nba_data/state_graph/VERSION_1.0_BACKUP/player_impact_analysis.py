#!/usr/bin/env python3
"""
선수 IN/OUT 영향 분석 (부상자 정보 기반)
정성적 가설을 정량적으로 검증

예시:
- Adams가 뛴 경기 vs 안 뛴 경기
- HOU의 득점, 승률 비교
"""

import json
from typing import Dict, List
from neo4j import GraphDatabase
from collections import defaultdict

class PlayerImpactAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_games_with_without_player(self, team: str, cutoff_date: str) -> Dict:
        """
        특정 날짜 기준으로 전후 경기 비교

        현재 한계: 부상자 정보가 historical data에 없음
        → ESPN preview는 내일 경기만 제공

        대안: 날짜 범위로 추정
        예: Adams는 2024-11-01 이후 HOU 합류
        """

        query_before = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date < date($cutoff_date)
          AND g.date >= date('2024-10-01')
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

        query_after = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date($cutoff_date)
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
            before = session.run(query_before, team=team, cutoff_date=cutoff_date).single()
            after = session.run(query_after, team=team, cutoff_date=cutoff_date).single()

            return {
                'without_player': dict(before) if before else None,
                'with_player': dict(after) if after else None
            }

    def analyze_player_impact(self, team: str, player_name: str, cutoff_date: str):
        """선수 영향 분석"""

        print("=" * 80)
        print(f"선수 영향 분석: {team} - {player_name}")
        print("=" * 80)
        print(f"\n가정: {cutoff_date} 이전 = {player_name} 없음")
        print(f"      {cutoff_date} 이후 = {player_name} 있음")
        print()

        result = self.get_games_with_without_player(team, cutoff_date)

        without = result['without_player']
        with_p = result['with_player']

        if not without or not with_p:
            print("⚠️  데이터 부족")
            return

        print("-" * 80)
        print(f"📊 {player_name} 없을 때 (시즌 초반)")
        print("-" * 80)
        print(f"  전적: {without['wins']}승 {without['games']-without['wins']}패 ({without['wins']/without['games']*100:.1f}%)")
        print(f"  평균 득점: {without['avg_score']}점")
        print(f"  평균 실점: {without['avg_allowed']}점")
        print(f"  평균 득실차: {without['avg_margin']:+.1f}점")
        print()

        print("-" * 80)
        print(f"📊 {player_name} 있을 때 (최근)")
        print("-" * 80)
        print(f"  전적: {with_p['wins']}승 {with_p['games']-with_p['wins']}패 ({with_p['wins']/with_p['games']*100:.1f}%)")
        print(f"  평균 득점: {with_p['avg_score']}점")
        print(f"  평균 실점: {with_p['avg_allowed']}점")
        print(f"  평균 득실차: {with_p['avg_margin']:+.1f}점")
        print()

        # 차이 계산
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

        # 해석
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
            print(f"  • 수비력 {allowed_diff:+.1f}점 악화 - 수비 약점 가능성")

        print()
        print("-" * 80)
        print("⚠️  주의사항")
        print("-" * 80)
        print(f"  • 샘플 크기: {player_name} 없을 때 {without['games']}경기, 있을 때 {with_p['games']}경기")
        print(f"  • 시즌 초반 vs 최근 비교 → 팀 케미스트리 발전 효과 포함")
        print(f"  • 상대 팀 강도 차이 미고려")
        print(f"  • {player_name}의 순수 효과만 분리하기 어려움")
        print()

def main():
    analyzer = PlayerImpactAnalyzer()

    try:
        # 예시: HOU - Adams (2024-11-01 합류 가정)
        print("분석 1: 휴스턴 - Adams 영향")
        analyzer.analyze_player_impact("HOU", "Adams", "2024-11-01")

        print("\n" + "=" * 80 + "\n")

        # 예시 2: BOS - Porzingis
        print("분석 2: 보스턴 - Porzingis 영향")
        analyzer.analyze_player_impact("BOS", "Porzingis", "2024-11-25")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
