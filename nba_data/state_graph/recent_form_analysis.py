#!/usr/bin/env python3
"""
최근 폼 & 트렌드 분석
- 최근 5경기 승률
- 연승/연패 streak
- 최근 득점 트렌드
- 홈/원정 최근 성적
- 모멘텀 지표
"""

import json
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from datetime import datetime

class RecentFormAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_recent_form(self, team: str, last_n: int = 5) -> Dict:
        """최근 N경기 폼"""
        query = """
        MATCH (g:GameState)
        WHERE g.home_team = $team OR g.away_team = $team
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_win
                  ELSE NOT g.home_win END AS won
        ORDER BY g.date DESC
        LIMIT $last_n
        WITH collect(won) AS results,
             collect(g.date) AS dates,
             sum(CASE WHEN won THEN 1 ELSE 0 END) AS wins,
             count(*) AS games
        RETURN wins, games,
               round(wins * 100.0 / games, 1) AS win_pct,
               results,
               dates[0] AS last_game_date
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, last_n=last_n)
            record = result.single()

            if not record:
                return None

            results = record['results']
            form_string = ''.join(['W' if w else 'L' for w in results])

            return {
                'wins': record['wins'],
                'games': record['games'],
                'win_pct': record['win_pct'],
                'form': form_string,  # "WWLWW"
                'last_game_date': str(record['last_game_date'])
            }

    def get_current_streak(self, team: str) -> Dict:
        """현재 연승/연패 streak"""
        query = """
        MATCH (g:GameState)
        WHERE g.home_team = $team OR g.away_team = $team
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_win
                  ELSE NOT g.home_win END AS won
        ORDER BY g.date DESC
        LIMIT 20
        WITH collect(won) AS results
        RETURN results
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            record = result.single()

            if not record:
                return {'streak': 0, 'type': 'none'}

            results = record['results']

            # 첫 번째 결과부터 연속된 승/패 카운트
            if not results:
                return {'streak': 0, 'type': 'none'}

            first_result = results[0]
            streak = 0

            for result in results:
                if result == first_result:
                    streak += 1
                else:
                    break

            return {
                'streak': streak,
                'type': 'win' if first_result else 'loss'
            }

    def get_scoring_trend(self, team: str, last_n: int = 5) -> Dict:
        """최근 득점 트렌드"""
        # 최근 N경기 평균
        query_recent = """
        MATCH (g:GameState)
        WHERE g.home_team = $team OR g.away_team = $team
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_score
                  ELSE g.away_score END AS points,
             CASE WHEN g.home_team = $team THEN g.away_score
                  ELSE g.home_score END AS points_allowed
        ORDER BY g.date DESC
        LIMIT $last_n
        RETURN round(avg(points), 1) AS avg_points,
               round(avg(points_allowed), 1) AS avg_allowed
        """

        # 시즌 전체 평균
        query_season = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date('2024-10-01')
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_score
                  ELSE g.away_score END AS points,
             CASE WHEN g.home_team = $team THEN g.away_score
                  ELSE g.home_score END AS points_allowed
        RETURN round(avg(points), 1) AS avg_points,
               round(avg(points_allowed), 1) AS avg_allowed
        """

        with self.driver.session() as session:
            recent = session.run(query_recent, team=team, last_n=last_n).single()
            season = session.run(query_season, team=team).single()

            if not recent or not season:
                return None

            recent_ppg = recent['avg_points']
            season_ppg = season['avg_points']
            recent_papg = recent['avg_allowed']
            season_papg = season['avg_allowed']

            return {
                'recent_ppg': recent_ppg,
                'season_ppg': season_ppg,
                'ppg_trend': round(recent_ppg - season_ppg, 1),  # +5.2 = 최근 더 많이 득점
                'recent_papg': recent_papg,
                'season_papg': season_papg,
                'papg_trend': round(recent_papg - season_papg, 1),  # -3.1 = 최근 더 적게 실점
                'offensive_trend': 'hot' if (recent_ppg - season_ppg) > 3 else 'cold' if (recent_ppg - season_ppg) < -3 else 'normal',
                'defensive_trend': 'hot' if (recent_papg - season_papg) < -3 else 'cold' if (recent_papg - season_papg) > 3 else 'normal'
            }

    def get_home_away_recent(self, team: str, location: str, last_n: int = 5) -> Dict:
        """최근 홈/원정 성적"""
        if location == 'home':
            query = """
            MATCH (g:GameState {home_team: $team})
            WITH g
            ORDER BY g.date DESC
            LIMIT $last_n
            WITH count(*) AS games,
                 sum(CASE WHEN g.home_win THEN 1 ELSE 0 END) AS wins,
                 avg(g.home_score - g.away_score) AS avg_margin
            RETURN games, wins,
                   round(wins * 100.0 / games, 1) AS win_pct,
                   round(avg_margin, 1) AS avg_margin
            """
        else:
            query = """
            MATCH (g:GameState {away_team: $team})
            WITH g
            ORDER BY g.date DESC
            LIMIT $last_n
            WITH count(*) AS games,
                 sum(CASE WHEN NOT g.home_win THEN 1 ELSE 0 END) AS wins,
                 avg(g.away_score - g.home_score) AS avg_margin
            RETURN games, wins,
                   round(wins * 100.0 / games, 1) AS win_pct,
                   round(avg_margin, 1) AS avg_margin
            """

        with self.driver.session() as session:
            result = session.run(query, team=team, last_n=last_n)
            record = result.single()

            if not record or record['games'] < 3:
                return None

            return {
                'games': record['games'],
                'wins': record['wins'],
                'win_pct': record['win_pct'],
                'avg_margin': record['avg_margin']
            }

    def get_recent_matchup(self, team1: str, team2: str, last_n: int = 3) -> Dict:
        """최근 맞대결 (최근 3경기)"""
        query = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team1 AND g.away_team = $team2)
           OR (g.home_team = $team2 AND g.away_team = $team1)
        WITH g
        ORDER BY g.date DESC
        LIMIT $last_n
        WITH collect({
            date: g.date,
            home: g.home_team,
            away: g.away_team,
            home_score: g.home_score,
            away_score: g.away_score,
            winner: CASE WHEN g.home_win THEN g.home_team ELSE g.away_team END
        }) AS games
        RETURN games
        """

        with self.driver.session() as session:
            result = session.run(query, team1=team1, team2=team2, last_n=last_n)
            record = result.single()

            if not record or not record['games']:
                return None

            games = record['games']
            team1_wins = sum(1 for g in games if g['winner'] == team1)

            return {
                'games': games,
                'team1_wins': team1_wins,
                'team2_wins': len(games) - team1_wins,
                'last_winner': games[0]['winner'],
                'last_date': str(games[0]['date'])
            }

    def get_momentum_score(self, team: str) -> float:
        """모멘텀 지표 (0-100, 높을수록 좋음)"""
        # 최근 10경기 승률
        form_10 = self.get_recent_form(team, 10)
        # 최근 5경기 승률
        form_5 = self.get_recent_form(team, 5)
        # 연승 streak
        streak = self.get_current_streak(team)

        if not form_10 or not form_5:
            return 50

        base_score = form_10['win_pct']

        # 최근 5경기가 10경기보다 좋으면 상승 모멘텀
        trend_bonus = (form_5['win_pct'] - form_10['win_pct']) * 0.5

        # 연승 보너스
        if streak['type'] == 'win':
            streak_bonus = min(streak['streak'] * 3, 15)
        elif streak['type'] == 'loss':
            streak_bonus = max(-streak['streak'] * 3, -15)
        else:
            streak_bonus = 0

        momentum = base_score + trend_bonus + streak_bonus
        return round(min(100, max(0, momentum)), 1)

    def generate_trend_report(self, game: Dict) -> Dict:
        """경기별 트렌드 리포트 생성"""
        home_team = game['home_team']['abbr']
        away_team = game['away_team']['abbr']

        # 최근 폼
        home_form = self.get_recent_form(home_team, 5)
        away_form = self.get_recent_form(away_team, 5)

        # 연승/연패
        home_streak = self.get_current_streak(home_team)
        away_streak = self.get_current_streak(away_team)

        # 득점 트렌드
        home_scoring = self.get_scoring_trend(home_team, 5)
        away_scoring = self.get_scoring_trend(away_team, 5)

        # 홈/원정 최근
        home_recent_home = self.get_home_away_recent(home_team, 'home', 5)
        away_recent_away = self.get_home_away_recent(away_team, 'away', 5)

        # 최근 맞대결
        recent_matchup = self.get_recent_matchup(home_team, away_team, 3)

        # 모멘텀
        home_momentum = self.get_momentum_score(home_team)
        away_momentum = self.get_momentum_score(away_team)

        return {
            'game_id': game['game_id'],
            'home_team': home_team,
            'away_team': away_team,
            'home_form': home_form,
            'away_form': away_form,
            'home_streak': home_streak,
            'away_streak': away_streak,
            'home_scoring': home_scoring,
            'away_scoring': away_scoring,
            'home_recent_home': home_recent_home,
            'away_recent_away': away_recent_away,
            'recent_matchup': recent_matchup,
            'home_momentum': home_momentum,
            'away_momentum': away_momentum
        }

    def format_trend_report(self, trends: Dict) -> str:
        """트렌드 리포트 포맷팅"""
        report = []

        report.append("=" * 90)
        report.append(f"🔥 최근 트렌드 분석: {trends['away_team']} @ {trends['home_team']}")
        report.append("=" * 90)
        report.append("")

        # 최근 폼
        report.append("-" * 90)
        report.append("📈 최근 5경기 폼")
        report.append("-" * 90)

        if trends['home_form']:
            hf = trends['home_form']
            report.append(f"  {trends['home_team']}: {hf['form']} ({hf['wins']}승 {hf['games']-hf['wins']}패, {hf['win_pct']}%)")

        if trends['away_form']:
            af = trends['away_form']
            report.append(f"  {trends['away_team']}: {af['form']} ({af['wins']}승 {af['games']-af['wins']}패, {af['win_pct']}%)")

        report.append("")

        # 연승/연패
        if trends['home_streak']['streak'] > 0 or trends['away_streak']['streak'] > 0:
            report.append("-" * 90)
            report.append("🔥 연승/연패 Streak")
            report.append("-" * 90)

            hs = trends['home_streak']
            if hs['streak'] > 0:
                streak_type = "연승" if hs['type'] == 'win' else "연패"
                emoji = "🔥" if hs['type'] == 'win' else "❄️"
                report.append(f"  {emoji} {trends['home_team']}: {hs['streak']} {streak_type}")

            as_ = trends['away_streak']
            if as_['streak'] > 0:
                streak_type = "연승" if as_['type'] == 'win' else "연패"
                emoji = "🔥" if as_['type'] == 'win' else "❄️"
                report.append(f"  {emoji} {trends['away_team']}: {as_['streak']} {streak_type}")

            report.append("")

        # 득점 트렌드
        report.append("-" * 90)
        report.append("📊 득점 트렌드 (최근 5경기 vs 시즌 평균)")
        report.append("-" * 90)

        if trends['home_scoring']:
            hs = trends['home_scoring']
            trend_emoji = "🔥" if hs['offensive_trend'] == 'hot' else "❄️" if hs['offensive_trend'] == 'cold' else "➡️"
            report.append(f"  {trends['home_team']} 공격: {hs['recent_ppg']}점 (시즌 {hs['season_ppg']}점) {trend_emoji} {hs['ppg_trend']:+.1f}")

            def_emoji = "🔥" if hs['defensive_trend'] == 'hot' else "❄️" if hs['defensive_trend'] == 'cold' else "➡️"
            report.append(f"  {trends['home_team']} 수비: {hs['recent_papg']}점 실점 (시즌 {hs['season_papg']}점) {def_emoji} {hs['papg_trend']:+.1f}")

        if trends['away_scoring']:
            as_ = trends['away_scoring']
            trend_emoji = "🔥" if as_['offensive_trend'] == 'hot' else "❄️" if as_['offensive_trend'] == 'cold' else "➡️"
            report.append(f"  {trends['away_team']} 공격: {as_['recent_ppg']}점 (시즌 {as_['season_ppg']}점) {trend_emoji} {as_['ppg_trend']:+.1f}")

            def_emoji = "🔥" if as_['defensive_trend'] == 'hot' else "❄️" if as_['defensive_trend'] == 'cold' else "➡️"
            report.append(f"  {trends['away_team']} 수비: {as_['recent_papg']}점 실점 (시즌 {as_['season_papg']}점) {def_emoji} {as_['papg_trend']:+.1f}")

        report.append("")

        # 홈/원정 최근
        report.append("-" * 90)
        report.append("🏠 홈/원정 최근 성적")
        report.append("-" * 90)

        if trends['home_recent_home']:
            hrh = trends['home_recent_home']
            report.append(f"  {trends['home_team']} 최근 홈: {hrh['wins']}승 {hrh['games']-hrh['wins']}패 ({hrh['win_pct']}%, 평균 {hrh['avg_margin']:+.1f}점)")

        if trends['away_recent_away']:
            ara = trends['away_recent_away']
            report.append(f"  {trends['away_team']} 최근 원정: {ara['wins']}승 {ara['games']-ara['wins']}패 ({ara['win_pct']}%, 평균 {ara['avg_margin']:+.1f}점)")

        report.append("")

        # 최근 맞대결
        if trends['recent_matchup']:
            report.append("-" * 90)
            report.append("⚔️  최근 맞대결 (최근 3경기)")
            report.append("-" * 90)

            rm = trends['recent_matchup']
            report.append(f"  전적: {trends['home_team']} {rm['team1_wins']}승 - {rm['team2_wins']}승 {trends['away_team']}")
            report.append(f"  최근 승자: {rm['last_winner']} ({rm['last_date']})")
            report.append("")

        # 모멘텀 지표
        report.append("-" * 90)
        report.append("⚡ 모멘텀 지표 (0-100, 높을수록 좋음)")
        report.append("-" * 90)

        mom_diff = trends['home_momentum'] - trends['away_momentum']

        report.append(f"  {trends['home_team']}: {trends['home_momentum']}")
        report.append(f"  {trends['away_team']}: {trends['away_momentum']}")

        if abs(mom_diff) >= 15:
            advantage_team = trends['home_team'] if mom_diff > 0 else trends['away_team']
            report.append(f"  💡 {advantage_team} 모멘텀 우위 ({abs(mom_diff):.1f}점 차이)")

        report.append("")
        report.append("=" * 90)
        report.append("")

        return "\n".join(report)

def main():
    """내일 경기 트렌드 분석"""
    analyzer = RecentFormAnalyzer()

    try:
        # 내일 경기 로드
        with open('/Users/js/g9/nba_data/state_graph/tomorrow_games.json', 'r') as f:
            games = json.load(f)

        print("=" * 90)
        print("🔥 내일 경기 최근 트렌드 분석")
        print("=" * 90)
        print("")

        all_reports = []

        for game in games:
            trends = analyzer.generate_trend_report(game)
            report = analyzer.format_trend_report(trends)
            all_reports.append(report)
            print(report)

        # 저장
        today = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"recent_trends_{today}.txt"
        filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_reports))

        print(f"✅ 트렌드 분석 저장: {filepath}")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
