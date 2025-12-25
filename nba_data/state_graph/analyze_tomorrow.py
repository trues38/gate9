#!/usr/bin/env python3
"""
내일 경기 자동 분석 리포트 생성
Neo4j에서 유사 경기 데이터를 조회하여 분석 컨텍스트 제공
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from neo4j import GraphDatabase

class TomorrowGameAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def load_tomorrow_games(self, filepath="tomorrow_games.json") -> List[Dict]:
        """내일 경기 스케줄 로드"""
        full_path = f"/Users/js/g9/nba_data/state_graph/{filepath}"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ {filepath} 파일이 없습니다. 먼저 fetch_tomorrow_games.py를 실행하세요.")
            return []

    def get_matchup_history(self, home_team: str, away_team: str) -> List[Dict]:
        """과거 매치업 전적"""
        query = """
        MATCH (game:GameState)
        WHERE game.home_team = $home_team AND game.away_team = $away_team
        RETURN
          game.date AS date,
          game.season AS season,
          game.home_score AS home_score,
          game.away_score AS away_score,
          game.home_win AS home_win,
          game.home_rest_days AS home_rest,
          game.away_rest_days AS away_rest
        ORDER BY game.date DESC
        LIMIT 5
        """

        with self.driver.session() as session:
            result = session.run(query, home_team=home_team, away_team=away_team)
            return [dict(record) for record in result]

    def get_matchup_stats(self, home_team: str, away_team: str) -> Optional[Dict]:
        """매치업 종합 통계"""
        query = """
        MATCH (game:GameState)
        WHERE game.home_team = $home_team AND game.away_team = $away_team
        WITH
          count(game) AS total_games,
          sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS home_wins,
          avg(game.home_score) AS avg_home_score,
          avg(game.away_score) AS avg_away_score,
          avg(game.home_score - game.away_score) AS avg_diff
        WHERE total_games > 0
        RETURN
          total_games,
          home_wins,
          total_games - home_wins AS away_wins,
          round(home_wins * 100.0 / total_games, 1) AS home_win_pct,
          round(avg_home_score, 1) AS avg_home_score,
          round(avg_away_score, 1) AS avg_away_score,
          round(avg_diff, 1) AS avg_point_diff
        """

        with self.driver.session() as session:
            result = session.run(query, home_team=home_team, away_team=away_team)
            record = result.single()
            return dict(record) if record else None

    def get_team_recent_form(self, team: str, limit: int = 5) -> List[Dict]:
        """최근 폼 (최근 N경기)"""
        query = """
        MATCH (game:GameState)
        WHERE game.home_team = $team OR game.away_team = $team
        WITH game,
             CASE
               WHEN game.home_team = $team THEN game.home_win
               ELSE NOT game.home_win
             END AS win,
             CASE
               WHEN game.home_team = $team THEN game.home_score - game.away_score
               ELSE game.away_score - game.home_score
             END AS point_diff,
             CASE
               WHEN game.home_team = $team THEN 'vs ' + game.away_team
               ELSE '@ ' + game.home_team
             END AS opponent
        ORDER BY game.date DESC
        LIMIT $limit
        RETURN
          game.date AS date,
          opponent,
          win,
          point_diff
        ORDER BY game.date DESC
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, limit=limit)
            return [dict(record) for record in result]

    def get_home_away_stats(self, team: str) -> Optional[Dict]:
        """홈/원정 별도 전적"""
        query = """
        MATCH (home_games:GameState {home_team: $team})
        WITH
          count(home_games) AS home_games_count,
          sum(CASE WHEN home_games.home_win THEN 1 ELSE 0 END) AS home_wins,
          avg(home_games.home_score) AS avg_home_score
        MATCH (away_games:GameState {away_team: $team})
        WITH
          home_games_count, home_wins, avg_home_score,
          count(away_games) AS away_games_count,
          sum(CASE WHEN NOT away_games.home_win THEN 1 ELSE 0 END) AS away_wins,
          avg(away_games.away_score) AS avg_away_score
        WHERE home_games_count > 0 AND away_games_count > 0
        RETURN
          home_games_count,
          home_wins,
          round(home_wins * 100.0 / home_games_count, 1) AS home_win_pct,
          round(avg_home_score, 1) AS avg_home_score,
          away_games_count,
          away_wins,
          round(away_wins * 100.0 / away_games_count, 1) AS away_win_pct,
          round(avg_away_score, 1) AS avg_away_score
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            record = result.single()
            return dict(record) if record else None

    def analyze_game(self, game: Dict) -> Dict:
        """개별 경기 분석"""
        home = game['home_team']['abbr']
        away = game['away_team']['abbr']

        print(f"\n🔍 분석 중: {away} @ {home}...")

        analysis = {
            'game_info': game,
            'matchup_history': self.get_matchup_history(home, away),
            'matchup_stats': self.get_matchup_stats(home, away),
            'home_recent': self.get_team_recent_form(home, 5),
            'away_recent': self.get_team_recent_form(away, 5),
            'home_stats': self.get_home_away_stats(home),
            'away_stats': self.get_home_away_stats(away)
        }

        return analysis

    def format_report(self, analysis: Dict) -> str:
        """리포트 텍스트 생성"""
        game = analysis['game_info']
        home = game['home_team']['abbr']
        away = game['away_team']['abbr']

        report = []
        report.append("=" * 80)
        report.append(f"📊 경기 분석: {away} @ {home}")
        report.append("=" * 80)
        report.append(f"날짜: {game['date']} {game['time']}")
        report.append(f"경기장: {game['venue']['name']}, {game['venue']['city']}")
        report.append(f"상태: {game['status']}")
        report.append("")

        # 매치업 전적
        report.append("-" * 80)
        report.append("📈 과거 매치업 전적")
        report.append("-" * 80)

        stats = analysis['matchup_stats']
        if stats and stats['total_games'] > 0:
            report.append(f"총 {stats['total_games']}경기: {home} {stats['home_wins']}승 - {away} {stats['away_wins']}승")
            report.append(f"{home} 홈 승률: {stats['home_win_pct']}%")
            report.append(f"평균 득점: {home} {stats['avg_home_score']} - {away} {stats['avg_away_score']}")
            report.append(f"평균 득점차: {stats['avg_point_diff']}점 ({home} 기준)")
            report.append("")

            report.append("최근 5경기:")
            for h in analysis['matchup_history']:
                date = h['date']
                result = 'W' if h['home_win'] else 'L'
                score = f"{h['home_score']}-{h['away_score']}"
                rest = f"(휴식: {home} {h['home_rest']}일, {away} {h['away_rest']}일)"
                report.append(f"  {date}: {home} {result} {score} {rest}")
        else:
            report.append("⚠️  과거 매치업 기록 없음")

        report.append("")

        # 홈 팀 최근 폼
        report.append("-" * 80)
        report.append(f"🏠 {home} ({game['home_team']['name']}) - 최근 5경기")
        report.append("-" * 80)

        home_stats = analysis['home_stats']
        if home_stats:
            report.append(f"홈 전적: {home_stats['home_wins']}-{home_stats['home_games_count'] - home_stats['home_wins']} ({home_stats['home_win_pct']}%, 평균 {home_stats['avg_home_score']}점)")
            report.append(f"원정 전적: {home_stats['away_wins']}-{home_stats['away_games_count'] - home_stats['away_wins']} ({home_stats['away_win_pct']}%, 평균 {home_stats['avg_away_score']}점)")
            report.append("")

        if analysis['home_recent']:
            wins = sum(1 for r in analysis['home_recent'] if r['win'])
            report.append(f"최근 5경기: {wins}승 {5-wins}패")
            for r in analysis['home_recent']:
                result = 'W' if r['win'] else 'L'
                diff = f"+{r['point_diff']}" if r['point_diff'] > 0 else str(r['point_diff'])
                report.append(f"  {r['date']}: {result} {r['opponent']} ({diff})")

        report.append("")

        # 원정 팀 최근 폼
        report.append("-" * 80)
        report.append(f"✈️  {away} ({game['away_team']['name']}) - 최근 5경기")
        report.append("-" * 80)

        away_stats = analysis['away_stats']
        if away_stats:
            report.append(f"홈 전적: {away_stats['home_wins']}-{away_stats['home_games_count'] - away_stats['home_wins']} ({away_stats['home_win_pct']}%, 평균 {away_stats['avg_home_score']}점)")
            report.append(f"원정 전적: {away_stats['away_wins']}-{away_stats['away_games_count'] - away_stats['away_wins']} ({away_stats['away_win_pct']}%, 평균 {away_stats['avg_away_score']}점)")
            report.append("")

        if analysis['away_recent']:
            wins = sum(1 for r in analysis['away_recent'] if r['win'])
            report.append(f"최근 5경기: {wins}승 {5-wins}패")
            for r in analysis['away_recent']:
                result = 'W' if r['win'] else 'L'
                diff = f"+{r['point_diff']}" if r['point_diff'] > 0 else str(r['point_diff'])
                report.append(f"  {r['date']}: {result} {r['opponent']} ({diff})")

        report.append("")
        report.append("=" * 80)
        report.append("")

        return "\n".join(report)

    def generate_report(self):
        """전체 리포트 생성"""
        print("=" * 80)
        print("내일 NBA 경기 자동 분석 리포트 생성")
        print("=" * 80)

        # 1. 내일 경기 로드
        games = self.load_tomorrow_games()
        if not games:
            return

        print(f"\n📅 총 {len(games)}경기 분석 시작...\n")

        # 2. 각 경기 분석
        all_reports = []
        for game in games:
            analysis = self.analyze_game(game)
            report = self.format_report(analysis)
            all_reports.append(report)

        # 3. 전체 리포트 통합
        full_report = "\n".join(all_reports)

        # 4. 출력
        print("\n\n")
        print(full_report)

        # 5. 파일 저장
        today = datetime.now().strftime("%Y%m%d")
        filename = f"tomorrow_analysis_{today}.txt"
        filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_report)

        print(f"\n✅ 리포트 저장: {filepath}")

        return full_report

def main():
    analyzer = TomorrowGameAnalyzer()

    try:
        analyzer.generate_report()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
