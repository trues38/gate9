#!/usr/bin/env python3
"""
프리뷰 정보 + 패턴 분석 통합 보고서
ESPN 프리뷰 (배당, 예측, 부상자) + Neo4j 패턴 분석
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from neo4j import GraphDatabase

class EnhancedGameAnalyzer:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ========================================================================
    # 패턴 분석 쿼리
    # ========================================================================

    def get_rest_day_pattern(self, team: str) -> List[Dict]:
        """휴식일별 승률 패턴"""
        query = """
        MATCH (game:GameState)
        WHERE game.home_team = $team
        WITH game.home_rest_days AS rest_days,
             sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS wins,
             count(game) AS games
        WHERE games >= 2
        RETURN rest_days, games, wins,
               round(wins * 100.0 / games, 1) AS win_pct
        ORDER BY rest_days

        UNION ALL

        MATCH (game:GameState)
        WHERE game.away_team = $team
        WITH game.away_rest_days AS rest_days,
             sum(CASE WHEN NOT game.home_win THEN 1 ELSE 0 END) AS wins,
             count(game) AS games
        WHERE games >= 2
        RETURN rest_days, games, wins,
               round(wins * 100.0 / games, 1) AS win_pct
        ORDER BY rest_days
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            return [dict(record) for record in result]

    def get_back_to_back_stats(self, team: str) -> Optional[Dict]:
        """백투백 경기 통계"""
        query = """
        MATCH (game:GameState)
        WHERE (game.home_team = $team AND game.home_rest_days = 0)
           OR (game.away_team = $team AND game.away_rest_days = 0)
        WITH game,
             CASE
               WHEN game.home_team = $team THEN game.home_win
               ELSE NOT game.home_win
             END AS win,
             CASE
               WHEN game.home_team = $team THEN game.home_score - game.away_score
               ELSE game.away_score - game.home_score
             END AS point_diff
        RETURN
          count(*) AS games,
          sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins,
          round(avg(point_diff), 1) AS avg_diff,
          round(sum(CASE WHEN win THEN 1 ELSE 0 END) * 100.0 / count(*), 1) AS win_pct
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            record = result.single()
            return dict(record) if record else None

    def get_recent_trend(self, team: str, limit: int = 10) -> Dict:
        """최근 경기 트렌드 (상승/하락)"""
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
             END AS point_diff
        ORDER BY game.date DESC
        LIMIT $limit
        RETURN
          count(*) AS games,
          sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins,
          round(avg(point_diff), 1) AS avg_diff
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, limit=limit)
            record = result.single()
            return dict(record) if record else {}

    def get_home_away_performance(self, team: str) -> Dict:
        """홈/원정 성적 비교"""
        query = """
        MATCH (home_games:GameState {home_team: $team})
        WITH
          count(home_games) AS home_games_count,
          sum(CASE WHEN home_games.home_win THEN 1 ELSE 0 END) AS home_wins,
          avg(home_games.home_score - home_games.away_score) AS home_avg_diff
        MATCH (away_games:GameState {away_team: $team})
        WITH
          home_games_count, home_wins, home_avg_diff,
          count(away_games) AS away_games_count,
          sum(CASE WHEN NOT away_games.home_win THEN 1 ELSE 0 END) AS away_wins,
          avg(away_games.away_score - away_games.home_score) AS away_avg_diff
        WHERE home_games_count > 0 AND away_games_count > 0
        RETURN
          home_games_count,
          home_wins,
          round(home_wins * 100.0 / home_games_count, 1) AS home_win_pct,
          round(home_avg_diff, 1) AS home_avg_diff,
          away_games_count,
          away_wins,
          round(away_wins * 100.0 / away_games_count, 1) AS away_win_pct,
          round(away_avg_diff, 1) AS away_avg_diff
        """

        with self.driver.session() as session:
            result = session.run(query, team=team)
            record = result.single()
            return dict(record) if record else {}

    def get_referee_stats(self, referee_name: str) -> Optional[Dict]:
        """심판 통계"""
        query = """
        MATCH (ref:Referee {name: $referee_name})<-[:OFFICIATED_BY]-(game:GameState)
        WITH ref,
             count(game) AS total_games,
             sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) AS home_wins,
             avg(game.home_score + game.away_score) AS avg_total_points
        WHERE total_games >= 5
        RETURN
          total_games,
          round(home_wins * 100.0 / total_games, 1) AS home_win_pct,
          round(avg_total_points, 1) AS avg_total_points
        """

        with self.driver.session() as session:
            result = session.run(query, referee_name=referee_name)
            record = result.single()
            return dict(record) if record else None

    # ========================================================================
    # 인사이트 생성
    # ========================================================================

    def generate_insights(self, home_team: str, away_team: str,
                         home_patterns: Dict, away_patterns: Dict,
                         preview: Dict) -> List[str]:
        """규칙 기반 인사이트 생성"""
        insights = []

        # 1. 최근 폼 비교
        home_trend = home_patterns.get('recent_trend', {})
        away_trend = away_patterns.get('recent_trend', {})

        if home_trend and away_trend:
            home_win_rate = (home_trend['wins'] / home_trend['games']) * 100
            away_win_rate = (away_trend['wins'] / away_trend['games']) * 100

            if home_win_rate >= 70:
                insights.append(f"✅ {home_team} 최근 강한 폼 ({home_trend['wins']}-{home_trend['games']-home_trend['wins']}, {home_win_rate:.0f}%)")
            elif home_win_rate <= 30:
                insights.append(f"⚠️  {home_team} 최근 부진 ({home_trend['wins']}-{home_trend['games']-home_trend['wins']}, {home_win_rate:.0f}%)")

            if away_win_rate >= 70:
                insights.append(f"✅ {away_team} 최근 강한 폼 ({away_trend['wins']}-{away_trend['games']-away_trend['wins']}, {away_win_rate:.0f}%)")
            elif away_win_rate <= 30:
                insights.append(f"⚠️  {away_team} 최근 부진 ({away_trend['wins']}-{away_trend['games']-away_trend['wins']}, {away_win_rate:.0f}%)")

        # 2. 홈/원정 강점
        home_perf = home_patterns.get('home_away', {})
        away_perf = away_patterns.get('home_away', {})

        if home_perf:
            if home_perf.get('home_win_pct', 0) >= 65:
                insights.append(f"🏠 {home_team} 강력한 홈 팀 ({home_perf['home_win_pct']}% 홈 승률)")

        if away_perf:
            if away_perf.get('away_win_pct', 0) >= 60:
                insights.append(f"✈️  {away_team} 강한 원정팀 ({away_perf['away_win_pct']}% 원정 승률)")
            elif away_perf.get('away_win_pct', 0) <= 35:
                insights.append(f"⚠️  {away_team} 원정 약세 ({away_perf['away_win_pct']}% 원정 승률)")

        # 3. 백투백 영향
        home_b2b = home_patterns.get('back_to_back')
        away_b2b = away_patterns.get('back_to_back')

        if home_b2b and home_b2b.get('games', 0) >= 3:
            insights.append(f"📊 {home_team} 백투백 {home_b2b['win_pct']}% 승률 (평균 {home_b2b['avg_diff']:+.1f}점)")

        if away_b2b and away_b2b.get('games', 0) >= 3:
            insights.append(f"📊 {away_team} 백투백 {away_b2b['win_pct']}% 승률 (평균 {away_b2b['avg_diff']:+.1f}점)")

        # 4. 배당/예측 기반
        if preview.get('odds'):
            spread = preview['odds'].get('spread', 0)
            if abs(spread) >= 8:
                favorite = home_team if spread < 0 else away_team
                insights.append(f"💰 배당: {favorite} 대승 예상 (스프레드 {abs(spread)})")

        if preview.get('predictions'):
            pred = preview['predictions']
            try:
                home_prob = float(pred.get('home_win_probability', 50))
                away_prob = float(pred.get('away_win_probability', 50))

                if abs(home_prob - away_prob) >= 30:
                    favorite = home_team if home_prob > away_prob else away_team
                    insights.append(f"📈 ESPN 예측: {favorite} 압도적 우세 ({max(home_prob, away_prob):.0f}%)")
            except (ValueError, TypeError):
                pass  # 예측 정보 파싱 실패 시 무시

        # 5. 부상자 영향
        injuries = preview.get('injuries', {'home': [], 'away': []})
        if len(injuries['home']) >= 3:
            insights.append(f"🏥 {home_team} 다수 부상자 ({len(injuries['home'])}명) - 전력 약화")
        if len(injuries['away']) >= 3:
            insights.append(f"🏥 {away_team} 다수 부상자 ({len(injuries['away'])}명) - 전력 약화")

        # 6. 심판 효과
        if preview.get('officials'):
            referee_name = preview['officials'][0]['name']
            ref_stats = self.get_referee_stats(referee_name)

            if ref_stats:
                home_win_pct = ref_stats['home_win_pct']
                if home_win_pct >= 60:
                    insights.append(f"👨‍⚖️ 심판 {referee_name}: 홈 유리 ({home_win_pct}% 홈 승률)")
                elif home_win_pct <= 45:
                    insights.append(f"👨‍⚖️ 심판 {referee_name}: 원정 유리 ({home_win_pct}% 홈 승률)")

        return insights

    # ========================================================================
    # 보고서 생성
    # ========================================================================

    def analyze_game_enhanced(self, game: Dict, preview: Dict) -> Dict:
        """프리뷰 + 패턴 통합 분석"""
        home = game['home_team']['abbr']
        away = game['away_team']['abbr']

        print(f"🔍 분석 중: {away} @ {home}...")

        # 패턴 분석
        home_patterns = {
            'rest_day': self.get_rest_day_pattern(home),
            'back_to_back': self.get_back_to_back_stats(home),
            'recent_trend': self.get_recent_trend(home, 10),
            'home_away': self.get_home_away_performance(home)
        }

        away_patterns = {
            'rest_day': self.get_rest_day_pattern(away),
            'back_to_back': self.get_back_to_back_stats(away),
            'recent_trend': self.get_recent_trend(away, 10),
            'home_away': self.get_home_away_performance(away)
        }

        # 인사이트 생성
        insights = self.generate_insights(home, away, home_patterns, away_patterns, preview)

        return {
            'game': game,
            'preview': preview,
            'home_patterns': home_patterns,
            'away_patterns': away_patterns,
            'insights': insights
        }

    def format_enhanced_report(self, analysis: Dict) -> str:
        """통합 보고서 포맷팅"""
        game = analysis['game']
        preview = analysis['preview']
        home = game['home_team']['abbr']
        away = game['away_team']['abbr']

        report = []
        report.append("=" * 90)
        report.append(f"📊 경기 분석: {away} @ {home}")
        report.append("=" * 90)
        report.append(f"날짜: {game['date']} {game['time']}")
        report.append(f"경기장: {game['venue']['name']}")
        report.append("")

        # === 프리뷰 정보 ===
        report.append("-" * 90)
        report.append("💰 ESPN 프리뷰")
        report.append("-" * 90)

        # 배당
        if preview.get('odds'):
            odds = preview['odds']
            report.append(f"\n배당 ({odds['provider']}):")
            report.append(f"  스프레드: {odds['spread']} (홈팀 기준)")
            report.append(f"  오버/언더: {odds['over_under']}")
            report.append(f"  머니라인: {home} {odds['home_moneyline']} / {away} {odds['away_moneyline']}")

        # 예측
        if preview.get('predictions'):
            pred = preview['predictions']
            try:
                home_prob = float(pred.get('home_win_probability', 0))
                away_prob = float(pred.get('away_win_probability', 0))
                home_score = float(pred.get('home_projected_score', 0))
                away_score = float(pred.get('away_projected_score', 0))

                report.append(f"\nESPN 승률 예측:")
                report.append(f"  {home}: {home_prob:.1f}% (예상 {home_score:.0f}점)")
                report.append(f"  {away}: {away_prob:.1f}% (예상 {away_score:.0f}점)")
            except (ValueError, TypeError):
                report.append(f"\nESPN 승률 예측: 정보 없음")

        # 부상자
        injuries = preview.get('injuries', {'home': [], 'away': []})
        if injuries['home'] or injuries['away']:
            report.append(f"\n🏥 부상자 명단:")
            for injury in injuries['home'] + injuries['away']:
                status_emoji = "🔴" if injury['status'] in ['Out', 'Doubtful'] else "🟡"
                report.append(f"  {status_emoji} [{injury['team']}] {injury['name']} - {injury['status']}: {injury['details']}")

        # 심판
        if preview.get('officials'):
            report.append(f"\n👨‍⚖️ 심판진:")
            for official in preview['officials']:
                report.append(f"  {official['position']}: {official['name']}")

                # 심판 통계 추가
                if official['order'] == 1:  # 주심만
                    ref_stats = self.get_referee_stats(official['name'])
                    if ref_stats:
                        report.append(f"    └ 과거 {ref_stats['total_games']}경기: 홈 승률 {ref_stats['home_win_pct']}%, 평균 총득점 {ref_stats['avg_total_points']}")
        else:
            report.append(f"\n⚠️  심판 정보 미공개 (경기 전 확인 필요)")

        report.append("")

        # === 패턴 분석 ===
        report.append("-" * 90)
        report.append(f"📈 패턴 분석 (과거 927게임 기반)")
        report.append("-" * 90)

        # 홈 팀
        home_patterns = analysis['home_patterns']
        report.append(f"\n🏠 {home} ({game['home_team']['name']}):")

        if home_patterns['home_away']:
            ha = home_patterns['home_away']
            report.append(f"  홈 전적: {ha['home_wins']}-{ha['home_games_count']-ha['home_wins']} ({ha['home_win_pct']}%, 평균 {ha['home_avg_diff']:+.1f}점)")

        if home_patterns['recent_trend']:
            rt = home_patterns['recent_trend']
            report.append(f"  최근 10경기: {rt['wins']}-{rt['games']-rt['wins']} (평균 {rt['avg_diff']:+.1f}점)")

        if home_patterns['back_to_back'] and home_patterns['back_to_back'].get('games', 0) >= 2:
            b2b = home_patterns['back_to_back']
            report.append(f"  백투백: {b2b['wins']}-{b2b['games']-b2b['wins']} ({b2b['win_pct']}%, 평균 {b2b['avg_diff']:+.1f}점)")

        # 원정 팀
        away_patterns = analysis['away_patterns']
        report.append(f"\n✈️  {away} ({game['away_team']['name']}):")

        if away_patterns['home_away']:
            ha = away_patterns['home_away']
            report.append(f"  원정 전적: {ha['away_wins']}-{ha['away_games_count']-ha['away_wins']} ({ha['away_win_pct']}%, 평균 {ha['away_avg_diff']:+.1f}점)")

        if away_patterns['recent_trend']:
            rt = away_patterns['recent_trend']
            report.append(f"  최근 10경기: {rt['wins']}-{rt['games']-rt['wins']} (평균 {rt['avg_diff']:+.1f}점)")

        if away_patterns['back_to_back'] and away_patterns['back_to_back'].get('games', 0) >= 2:
            b2b = away_patterns['back_to_back']
            report.append(f"  백투백: {b2b['wins']}-{b2b['games']-b2b['wins']} ({b2b['win_pct']}%, 평균 {b2b['avg_diff']:+.1f}점)")

        report.append("")

        # === 인사이트 ===
        report.append("-" * 90)
        report.append("💡 핵심 인사이트")
        report.append("-" * 90)

        for insight in analysis['insights']:
            report.append(f"  {insight}")

        report.append("")
        report.append("=" * 90)
        report.append("")

        return "\n".join(report)

    def generate_full_report(self):
        """전체 보고서 생성"""
        print("=" * 90)
        print("프리뷰 + 패턴 분석 통합 보고서 생성")
        print("=" * 90)

        # 내일 경기 로드
        games_path = "/Users/js/g9/nba_data/state_graph/tomorrow_games.json"
        with open(games_path, 'r', encoding='utf-8') as f:
            games = json.load(f)

        # 프리뷰 정보 로드
        preview_path = "/Users/js/g9/nba_data/state_graph/tomorrow_previews.json"
        try:
            with open(preview_path, 'r', encoding='utf-8') as f:
                previews = json.load(f)
        except FileNotFoundError:
            print("❌ 프리뷰 정보가 없습니다. 먼저 fetch_game_preview.py를 실행하세요.")
            return

        # 프리뷰를 game_id로 매핑
        preview_map = {p['game_id']: p for p in previews}

        # 분석
        all_reports = []
        for game in games:
            game_id = game['game_id']
            preview = preview_map.get(game_id, {})

            analysis = self.analyze_game_enhanced(game, preview)
            report = self.format_enhanced_report(analysis)
            all_reports.append(report)

        # 통합 리포트
        full_report = "\n".join(all_reports)

        # 출력
        print("\n\n")
        print(full_report)

        # 저장
        today = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"enhanced_analysis_{today}.txt"
        filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_report)

        print(f"\n✅ 리포트 저장: {filepath}")

def main():
    analyzer = EnhancedGameAnalyzer()

    try:
        analyzer.generate_full_report()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
