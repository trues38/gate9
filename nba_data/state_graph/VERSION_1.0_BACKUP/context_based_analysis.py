#!/usr/bin/env python3
"""
컨텍스트 기반 패턴 분석
내일 경기의 실제 컨텍스트를 과거 패턴과 매칭하여 예측
"""

import json
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from datetime import datetime

class ContextBasedAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ========================================================================
    # 컨텍스트별 과거 패턴 쿼리
    # ========================================================================

    def get_rest_day_performance(self, team: str, rest_days: int, home_away: str) -> Optional[Dict]:
        """특정 휴식일에서의 팀 성적"""
        if home_away == "home":
            query = """
            MATCH (game:GameState {home_team: $team})
            WHERE game.home_rest_days = $rest_days
            WITH count(game) AS games,
                 sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS wins,
                 avg(game.home_score - game.away_score) AS avg_diff
            WHERE games >= 2
            RETURN games, wins,
                   round(wins * 100.0 / games, 1) AS win_pct,
                   round(avg_diff, 1) AS avg_diff
            """
        else:
            query = """
            MATCH (game:GameState {away_team: $team})
            WHERE game.away_rest_days = $rest_days
            WITH count(game) AS games,
                 sum(CASE WHEN NOT game.home_win THEN 1 ELSE 0 END) AS wins,
                 avg(game.away_score - game.home_score) AS avg_diff
            WHERE games >= 2
            RETURN games, wins,
                   round(wins * 100.0 / games, 1) AS win_pct,
                   round(avg_diff, 1) AS avg_diff
            """

        with self.driver.session() as session:
            result = session.run(query, team=team, rest_days=rest_days)
            record = result.single()
            return dict(record) if record else None

    def get_injury_impact(self, team: str, injury_count_range: str) -> Optional[Dict]:
        """부상자 수별 영향 (간접 추정)"""
        # 부상자 수는 직접 저장 안되어 있으므로, 최근 성적으로 대체
        # 실제로는 부상자 수를 GameState에 추가해야 정확함
        query = """
        MATCH (game:GameState)
        WHERE game.home_team = $team OR game.away_team = $team
        WITH game,
             CASE
               WHEN game.home_team = $team THEN game.home_win
               ELSE NOT game.home_win
             END AS win
        RETURN count(*) AS games,
               sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins,
               round(sum(CASE WHEN win THEN 1 ELSE 0 END) * 100.0 / count(*), 1) AS win_pct
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            record = result.single()
            return dict(record) if record else None

    def get_referee_home_bias(self, referee_name: str) -> Optional[Dict]:
        """심판별 홈 편향"""
        query = """
        MATCH (ref:Referee {name: $referee_name})<-[:OFFICIATED_BY]-(game:GameState)
        WITH count(game) AS games,
             sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS home_wins,
             avg(game.home_score + game.away_score) AS avg_total_points
        WHERE games >= 5
        RETURN games,
               round(home_wins * 100.0 / games, 1) AS home_win_pct,
               round(avg_total_points, 1) AS avg_total_points
        """

        with self.driver.session() as session:
            result = session.run(query, referee_name=referee_name)
            record = result.single()
            return dict(record) if record else None

    def get_rest_advantage_impact(self, rest_diff: int) -> Optional[Dict]:
        """휴식일 차이의 영향"""
        query = """
        MATCH (game:GameState)
        WHERE game.home_rest_days - game.away_rest_days = $rest_diff
        WITH count(game) AS games,
             sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS home_wins
        WHERE games >= 3
        RETURN games,
               round(home_wins * 100.0 / games, 1) AS home_win_pct
        """

        with self.driver.session() as session:
            result = session.run(query, rest_diff=rest_diff)
            record = result.single()
            return dict(record) if record else None

    # ========================================================================
    # 컨텍스트 기반 인사이트 생성
    # ========================================================================

    def generate_context_insights(self, context: Dict, home_team: str, away_team: str) -> List[str]:
        """실제 컨텍스트 기반 인사이트"""
        insights = []

        # 1. 휴식일 패턴
        home_rest_perf = self.get_rest_day_performance(
            home_team, context['home_rest_days'], 'home'
        )
        away_rest_perf = self.get_rest_day_performance(
            away_team, context['away_rest_days'], 'away'
        )

        if home_rest_perf and home_rest_perf['games'] >= 3:
            insights.append(
                f"📅 {home_team} 휴식 {context['home_rest_days']}일: "
                f"{home_rest_perf['win_pct']}% 승률 "
                f"(평균 {home_rest_perf['avg_diff']:+.1f}점, {home_rest_perf['games']}경기 기준)"
            )

        if away_rest_perf and away_rest_perf['games'] >= 3:
            insights.append(
                f"📅 {away_team} 휴식 {context['away_rest_days']}일: "
                f"{away_rest_perf['win_pct']}% 승률 "
                f"(평균 {away_rest_perf['avg_diff']:+.1f}점, {away_rest_perf['games']}경기 기준)"
            )

        # 2. 백투백 효과
        if context['home_back_to_back']:
            insights.append(f"🔴 {home_team} 백투백 경기 - 체력 부담 증가")

        if context['away_back_to_back']:
            insights.append(f"🔴 {away_team} 백투백 경기 - 체력 부담 증가")

        # 3. 휴식일 우위
        rest_diff = context['rest_advantage']
        if abs(rest_diff) >= 2:
            rest_impact = self.get_rest_advantage_impact(rest_diff)
            if rest_impact and rest_impact['games'] >= 3:
                advantage_team = home_team if rest_diff > 0 else away_team
                insights.append(
                    f"⚖️ {advantage_team} 휴식 우위 {abs(rest_diff)}일: "
                    f"과거 이런 경우 홈 {rest_impact['home_win_pct']}% 승률 "
                    f"({rest_impact['games']}경기 기준)"
                )

        # 4. 부상자 영향
        if context['home_injuries_count'] >= 4:
            insights.append(
                f"🏥 {home_team} 다수 부상자 ({context['home_injuries_count']}명) - "
                f"전력 약화 예상"
            )

        if context['away_injuries_count'] >= 4:
            insights.append(
                f"🏥 {away_team} 다수 부상자 ({context['away_injuries_count']}명) - "
                f"전력 약화 예상"
            )

        # 5. 심판 효과
        if context['has_referee']:
            ref_stats = self.get_referee_home_bias(context['referee'])
            if ref_stats and ref_stats['games'] >= 10:
                home_pct = ref_stats['home_win_pct']

                if home_pct >= 55:
                    insights.append(
                        f"👨‍⚖️ 심판 {context['referee']}: 홈 유리 "
                        f"({home_pct}% 홈 승률, {ref_stats['games']}경기 기준)"
                    )
                elif home_pct <= 45:
                    insights.append(
                        f"👨‍⚖️ 심판 {context['referee']}: 원정 유리 "
                        f"({home_pct}% 홈 승률, {ref_stats['games']}경기 기준)"
                    )
                else:
                    insights.append(
                        f"👨‍⚖️ 심판 {context['referee']}: 중립적 "
                        f"({home_pct}% 홈 승률)"
                    )

        return insights

    # ========================================================================
    # 예측 생성
    # ========================================================================

    def generate_prediction(self, context: Dict, insights: List[str]) -> Dict:
        """컨텍스트와 인사이트 기반 예측"""
        home_team = context['home_team']
        away_team = context['away_team']

        # 각 요소별 점수 계산
        home_score = 50  # 기본 50%
        factors = []

        # 휴식일 우위
        rest_diff = context['rest_advantage']
        if rest_diff >= 2:
            home_score += 5 * rest_diff
            factors.append(f"휴식 우위 +{5 * rest_diff}%")
        elif rest_diff <= -2:
            home_score += 5 * rest_diff  # 마이너스
            factors.append(f"휴식 열세 {5 * rest_diff}%")

        # 백투백 페널티
        if context['home_back_to_back']:
            home_score -= 10
            factors.append("백투백 -10%")

        if context['away_back_to_back']:
            home_score += 10
            factors.append("상대 백투백 +10%")

        # 부상자 영향
        injury_diff = context['away_injuries_count'] - context['home_injuries_count']
        if abs(injury_diff) >= 2:
            home_score += injury_diff * 3
            if injury_diff > 0:
                factors.append(f"부상자 적음 +{injury_diff * 3}%")
            else:
                factors.append(f"부상자 많음 {injury_diff * 3}%")

        # 심판 효과
        if context['has_referee']:
            ref_stats = self.get_referee_home_bias(context['referee'])
            if ref_stats and ref_stats['games'] >= 10:
                ref_bias = ref_stats['home_win_pct'] - 50
                home_score += ref_bias * 0.5
                if abs(ref_bias) >= 5:
                    factors.append(f"심판 효과 {ref_bias * 0.5:+.1f}%")

        # 범위 제한
        home_score = max(10, min(90, home_score))

        return {
            'home_win_probability': round(home_score, 1),
            'away_win_probability': round(100 - home_score, 1),
            'factors': factors,
            'confidence': 'high' if abs(home_score - 50) >= 15 else 'medium' if abs(home_score - 50) >= 8 else 'low'
        }

    # ========================================================================
    # 보고서 생성
    # ========================================================================

    def generate_context_report(self):
        """컨텍스트 기반 분석 보고서"""
        # 컨텍스트 로드
        context_path = "/Users/js/g9/nba_data/state_graph/tomorrow_contexts.json"
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                contexts = json.load(f)
        except FileNotFoundError:
            print("❌ tomorrow_contexts.json이 없습니다. 먼저 calculate_game_context.py를 실행하세요.")
            return

        # 경기 정보 로드
        games_path = "/Users/js/g9/nba_data/state_graph/tomorrow_games.json"
        with open(games_path, 'r', encoding='utf-8') as f:
            games = json.load(f)

        game_map = {g['game_id']: g for g in games}

        # 보고서 생성
        reports = []

        for context in contexts:
            game = game_map.get(context['game_id'])
            if not game:
                continue

            home_team = context['home_team']
            away_team = context['away_team']

            # 인사이트 생성
            insights = self.generate_context_insights(context, home_team, away_team)

            # 예측 생성
            prediction = self.generate_prediction(context, insights)

            # 리포트 포맷팅
            report = []
            report.append("=" * 90)
            report.append(f"🎯 컨텍스트 기반 분석: {away_team} @ {home_team}")
            report.append("=" * 90)
            report.append(f"날짜: {context['game_date']}")
            report.append("")

            # 실제 컨텍스트
            report.append("-" * 90)
            report.append("📋 실제 경기 컨텍스트")
            report.append("-" * 90)

            rest_emoji_home = "🔴" if context['home_back_to_back'] else "🟢"
            rest_emoji_away = "🔴" if context['away_back_to_back'] else "🟢"

            report.append(f"\n휴식일:")
            report.append(f"  {rest_emoji_home} {home_team}: {context['home_rest_days']}일" +
                         (" (백투백)" if context['home_back_to_back'] else ""))
            report.append(f"  {rest_emoji_away} {away_team}: {context['away_rest_days']}일" +
                         (" (백투백)" if context['away_back_to_back'] else ""))

            if abs(context['rest_advantage']) >= 1:
                adv_team = home_team if context['rest_advantage'] > 0 else away_team
                report.append(f"  → {adv_team} 휴식 우위 ({abs(context['rest_advantage'])}일)")

            report.append(f"\n부상자:")
            report.append(f"  {home_team}: {context['home_injuries_count']}명")
            report.append(f"  {away_team}: {context['away_injuries_count']}명")

            if context['has_referee']:
                report.append(f"\n심판: {context['referee']}")
            else:
                report.append(f"\n심판: 미공개")

            report.append("")

            # 과거 패턴 기반 인사이트
            report.append("-" * 90)
            report.append("📊 과거 패턴 기반 인사이트")
            report.append("-" * 90)
            report.append("")

            for insight in insights:
                report.append(f"  {insight}")

            report.append("")

            # 예측
            report.append("-" * 90)
            report.append("🎯 컨텍스트 기반 예측")
            report.append("-" * 90)
            report.append("")

            report.append(f"승률 예측:")
            report.append(f"  {home_team}: {prediction['home_win_probability']}%")
            report.append(f"  {away_team}: {prediction['away_win_probability']}%")
            report.append(f"\n신뢰도: {prediction['confidence'].upper()}")

            if prediction['factors']:
                report.append(f"\n주요 요인:")
                for factor in prediction['factors']:
                    report.append(f"  • {factor}")

            report.append("")
            report.append("=" * 90)
            report.append("")

            reports.append("\n".join(report))

        # 전체 리포트 통합
        full_report = "\n".join(reports)

        # 출력
        print(full_report)

        # 저장
        today = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"context_based_analysis_{today}.txt"
        filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_report)

        print(f"\n✅ 컨텍스트 기반 분석 저장: {filepath}")

def main():
    analyzer = ContextBasedAnalyzer()

    try:
        analyzer.generate_context_report()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
