#!/usr/bin/env python3
"""
G9 Graph RAG Report Generator (리얼타임 제외, 5인 회의 제외)
VPS Neo4j 데이터 기반 분석 리포트 생성
"""

from neo4j import GraphDatabase
from datetime import datetime
import json
import sys
import os
import requests
from lineup_collector import LineupCollector
from referee_stats_collector import RefereeStatsCollector
from odds_api_adapter import OddsAPIAdapter

class GraphRAGReportGenerator:
    """Graph RAG 기반 리포트 생성기"""

    # 팀 약자 → Odds API 풀네임 매핑
    TEAM_NAME_MAPPING = {
        'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',
        'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
        'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
        'GS': 'Golden State Warriors', 'GSW': 'Golden State Warriors',
        'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
        'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers',
        'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks',
        'MIN': 'Minnesota Timberwolves', 'NO': 'New Orleans Pelicans',
        'NOP': 'New Orleans Pelicans', 'NY': 'New York Knicks', 'NYK': 'New York Knicks',
        'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic',
        'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns', 'POR': 'Portland Trail Blazers',
        'SAC': 'Sacramento Kings', 'SA': 'San Antonio Spurs', 'SAS': 'San Antonio Spurs',
        'TOR': 'Toronto Raptors', 'UTAH': 'Utah Jazz', 'UTA': 'Utah Jazz',
        'WSH': 'Washington Wizards', 'WAS': 'Washington Wizards'
    }

    def __init__(self):
        # VPS Neo4j 연결 (SSH Tunnel via localhost)
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_password = "nba_vultr_2025"
        self.driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=("neo4j", self.neo4j_password)
        )

        # 라인업 및 심판 수집기
        self.lineup_collector = LineupCollector()
        self.referee_collector = RefereeStatsCollector()

        # Odds API (환경변수 또는 기본값)
        odds_api_key = os.environ.get('ODDS_API_KEY', 'b01049f1f29d61c53189799c40d66f69')
        try:
            self.odds_adapter = OddsAPIAdapter(api_key=odds_api_key)
        except ValueError:
            print("⚠️ Odds API key not available - odds data will be skipped")
            self.odds_adapter = None

        # OpenRouter API
        self.openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
        if not self.openrouter_api_key:
            print("⚠️ OPENROUTER_API_KEY not found - narrative analysis will be skipped")

    def close(self):
        self.driver.close()

    def get_team_info(self, team_abbr):
        """팀 정보 조회 + 최근 전적 계산"""
        with self.driver.session() as session:
            # 팀 기본 정보
            query = """
            MATCH (t:Team {team_abbr: $abbr})
            RETURN t
            LIMIT 1
            """
            result = session.run(query, abbr=team_abbr)
            record = result.single()

            if not record:
                return None

            team = record['t']

            # 최근 10경기 전적 계산
            stats_query = """
            MATCH (g:Game)
            WHERE (g.home_team = $abbr OR g.away_team = $abbr)
              AND g.home_score IS NOT NULL
              AND g.away_score IS NOT NULL
            WITH g ORDER BY g.date DESC LIMIT 10
            RETURN
                count(g) as total_games,
                sum(CASE
                    WHEN (g.home_team = $abbr AND g.home_score > g.away_score)
                      OR (g.away_team = $abbr AND g.away_score > g.home_score)
                    THEN 1 ELSE 0 END) as wins,
                avg(CASE WHEN g.home_team = $abbr THEN g.home_score ELSE g.away_score END) as avg_scored,
                avg(CASE WHEN g.home_team = $abbr THEN g.away_score ELSE g.home_score END) as avg_allowed
            """
            stats_result = session.run(stats_query, abbr=team_abbr)
            stats_record = stats_result.single()

            wins = stats_record['wins'] if stats_record else 0
            total = stats_record['total_games'] if stats_record else 0
            losses = total - wins

            return {
                'name': team.get('name', team_abbr),
                'abbreviation': team_abbr,
                'record': f"{wins}-{losses}" if total > 0 else "N/A",
                'win_pct': f"{(wins/total*100):.1f}%" if total > 0 else "N/A",
                'avg_scored': f"{stats_record['avg_scored']:.1f}" if stats_record and stats_record['avg_scored'] else "N/A",
                'avg_allowed': f"{stats_record['avg_allowed']:.1f}" if stats_record and stats_record['avg_allowed'] else "N/A"
            }

    def get_h2h_history(self, home_team, away_team):
        """최근 맞대결 기록"""
        with self.driver.session() as session:
            query = """
            MATCH (g:Game)
            WHERE (g.home_team = $home AND g.away_team = $away)
               OR (g.home_team = $away AND g.away_team = $home)
            RETURN g
            ORDER BY g.date DESC
            LIMIT 5
            """
            result = session.run(query, home=home_team, away=away_team)

            games = []
            for record in result:
                game = record['g']
                games.append({
                    'date': game.get('date', 'N/A'),
                    'home_team': game.get('home_team'),
                    'away_team': game.get('away_team'),
                    'home_score': game.get('home_score'),
                    'away_score': game.get('away_score')
                })

            return games

    def get_recent_games(self, team_abbr, limit=5):
        """최근 경기 기록"""
        with self.driver.session() as session:
            query = """
            MATCH (g:Game)
            WHERE g.home_team = $team OR g.away_team = $team
            RETURN g
            ORDER BY g.date DESC
            LIMIT $limit
            """
            result = session.run(query, team=team_abbr, limit=limit)

            games = []
            for record in result:
                game = record['g']
                is_home = game.get('home_team') == team_abbr
                opponent = game.get('away_team') if is_home else game.get('home_team')
                
                # 결과 판정
                home_score = game.get('home_score', 0)
                away_score = game.get('away_score', 0)
                
                if is_home:
                    result_str = 'W' if home_score > away_score else 'L'
                else:
                    result_str = 'W' if away_score > home_score else 'L'

                games.append({
                    'date': game.get('date', 'N/A'),
                    'opponent': opponent,
                    'location': 'HOME' if is_home else 'AWAY',
                    'result': result_str,
                    'score': f'{home_score}-{away_score}'
                })

            return games

    def get_key_players(self, team_abbr, lineup_data=None):
        """주요 선수 정보 - Lineup 기반"""
        # Lineup에서 starters 추출
        if lineup_data and lineup_data.get('starters'):
            players = []
            for starter in lineup_data['starters']:
                players.append({
                    'name': starter.get('name', 'Unknown'),
                    'position': starter.get('position', 'N/A')
                })
            return players

        # Fallback: Neo4j에서 가져오기 (별로지만 있는게 나음)
        with self.driver.session() as session:
            query = """
            MATCH (p:Player)-[:PLAYS_FOR]->(t:Team {team_abbr: $abbr})
            RETURN p.name as name
            LIMIT 5
            """
            result = session.run(query, abbr=team_abbr)

            players = []
            for record in result:
                players.append({
                    'name': record.get('name', 'Unknown'),
                    'position': 'N/A'
                })

            return players if players else []

    def analyze_matchup_insights(self, analysis):
        """Graph 데이터 기반 매치업 인사이트 분석"""
        insights = {
            'h2h_edge': None,
            'form_edge': None,
            'spread_analysis': None,
            'total_analysis': None,
            'key_factors': [],
            'deep_dive': {},
            'risk_factors': [],
            'scenarios': {}
        }

        # H2H 분석
        h2h = analysis.get('h2h_history', [])
        if len(h2h) >= 3:
            # 현재 매치업 기준 팀별 승수 계산 (홈/어웨이 무관하게 전체 승수)
            current_home_team = analysis['home_team']['abbreviation']
            current_away_team = analysis['away_team']['abbreviation']

            home_team_wins = 0
            away_team_wins = 0
            valid_games = 0

            for g in h2h:
                home_score = g.get('home_score', 0)
                away_score = g.get('away_score', 0)

                # 점수가 없는 경기는 제외 (N/A 또는 예정된 경기)
                if not home_score or not away_score:
                    continue

                valid_games += 1
                game_home_team = g['home_team']

                # 현재 홈팀(LAL, LAC 등)이 이 게임에서 이겼는지 확인
                if game_home_team == current_home_team:
                    # 현재 홈팀이 그 게임에서도 홈팀이었음
                    if home_score > away_score:
                        home_team_wins += 1
                    else:
                        away_team_wins += 1
                else:
                    # 현재 홈팀이 그 게임에서는 어웨이팀이었음
                    if away_score > home_score:
                        home_team_wins += 1
                    else:
                        away_team_wins += 1

            if valid_games >= 3:
                if home_team_wins > away_team_wins:
                    insights['h2h_edge'] = f"{analysis['home_team']['name']} dominates H2H ({home_team_wins}-{away_team_wins} in last {valid_games})"
                elif away_team_wins > home_team_wins:
                    insights['h2h_edge'] = f"{analysis['away_team']['name']} dominates H2H ({away_team_wins}-{home_team_wins} in last {valid_games})"
                else:
                    insights['h2h_edge'] = f"Even matchup ({home_team_wins}-{away_team_wins} split)"

        # Recent Form 분석
        home_recent = analysis.get('home_recent_games', [])
        away_recent = analysis.get('away_recent_games', [])

        if home_recent:
            home_wins = sum(1 for g in home_recent if g.get('result') == 'W')
            home_form = f"{home_wins}-{len(home_recent)-home_wins}"
        else:
            home_form = "N/A"

        if away_recent:
            away_wins = sum(1 for g in away_recent if g.get('result') == 'W')
            away_form = f"{away_wins}-{len(away_recent)-away_wins}"
        else:
            away_form = "N/A"

        if home_recent and away_recent:
            if home_wins > away_wins:
                insights['form_edge'] = f"{analysis['home_team']['name']} hotter ({home_form} vs {away_form} L5)"
            elif away_wins > home_wins:
                insights['form_edge'] = f"{analysis['away_team']['name']} hotter ({away_form} vs {home_form} L5)"
            else:
                insights['form_edge'] = f"Similar form ({home_form} vs {away_form})"

        # Odds 기반 분석
        odds_data = analysis.get('odds_data')
        if odds_data and h2h:
            # Spread 분석
            if 'spreads' in odds_data:
                spreads = odds_data['spreads']
                home_spread = spreads.get('home', {}).get('point', 0)
                away_spread = spreads.get('away', {}).get('point', 0)

                # H2H 평균 승차 계산 (현재 홈팀 관점)
                margins = []
                for g in h2h:
                    home_score = g.get('home_score', 0)
                    away_score = g.get('away_score', 0)
                    if not home_score or not away_score:
                        continue

                    game_home_team = g['home_team']
                    current_home_team = analysis['home_team']['abbreviation']

                    # 현재 홈팀 관점에서 승차 계산
                    if game_home_team == current_home_team:
                        margin = home_score - away_score
                    else:
                        margin = away_score - home_score

                    margins.append(margin)

                if margins and len(margins) >= 3:
                    avg_margin = sum(margins) / len(margins)

                    if abs(home_spread) > 0:
                        if abs(avg_margin) < abs(home_spread) - 3:
                            insights['spread_analysis'] = f"Spread {home_spread} looks HIGH (H2H avg margin: {avg_margin:.1f})"
                        elif abs(avg_margin) > abs(home_spread) + 5:
                            insights['spread_analysis'] = f"Spread {home_spread} looks LOW (H2H avg margin: {avg_margin:.1f})"

            # Total 분석
            if 'totals' in odds_data:
                totals = odds_data['totals']
                total_line = totals.get('over', {}).get('point', 0)

                if total_line > 0:
                    total_scores = [g.get('home_score', 0) + g.get('away_score', 0)
                                   for g in h2h
                                   if g.get('home_score') and g.get('away_score')]

                    if total_scores and len(total_scores) >= 3:
                        avg_total = sum(total_scores) / len(total_scores)

                        if avg_total < total_line - 10:
                            insights['total_analysis'] = f"LEAN Under {total_line} (H2H avg: {avg_total:.1f})"
                        elif avg_total > total_line + 10:
                            insights['total_analysis'] = f"LEAN Over {total_line} (H2H avg: {avg_total:.1f})"

        # Key Factors
        if home_recent and len(home_recent) >= 3:
            home_streak = 0
            for game in home_recent:
                if game.get('result') == 'W':
                    home_streak += 1
                else:
                    break

            if home_streak >= 3:
                insights['key_factors'].append(f"{analysis['home_team']['name']} on {home_streak}-game win streak")

        if away_recent and len(away_recent) >= 3:
            away_streak = 0
            for game in away_recent:
                if game.get('result') == 'W':
                    away_streak += 1
                else:
                    break

            if away_streak >= 3:
                insights['key_factors'].append(f"{analysis['away_team']['name']} on {away_streak}-game win streak")

        # === Deep Dive: 강점/약점/패턴 분석 ===
        home_team = analysis['home_team']
        away_team = analysis['away_team']

        # 1. 공수 매치업 분석 (공격 vs 상대 수비)
        home_scored = float(home_team.get('avg_scored', 0)) if home_team.get('avg_scored') != 'N/A' else 0
        home_allowed = float(home_team.get('avg_allowed', 0)) if home_team.get('avg_allowed') != 'N/A' else 0
        away_scored = float(away_team.get('avg_scored', 0)) if away_team.get('avg_scored') != 'N/A' else 0
        away_allowed = float(away_team.get('avg_allowed', 0)) if away_team.get('avg_allowed') != 'N/A' else 0

        # 홈팀 공격 vs 원정팀 수비 (공격이 수비보다 10점 이상 높으면 공격 유리)
        if home_scored > 0 and away_allowed > 0:
            diff = home_scored - away_allowed
            if diff > 10:
                insights['deep_dive']['home_offense_edge'] = f"{home_team['name']} 공격({home_scored:.1f}) vs {away_team['name']} 수비({away_allowed:.1f}) = {diff:+.1f}점 우위"

        # 원정팀 공격 vs 홈팀 수비
        if away_scored > 0 and home_allowed > 0:
            diff = away_scored - home_allowed
            if diff > 10:
                insights['deep_dive']['away_offense_edge'] = f"{away_team['name']} 공격({away_scored:.1f}) vs {home_team['name']} 수비({home_allowed:.1f}) = {diff:+.1f}점 우위"

        # 2. 페이스/트렌드 분석 (최근 경기 총점)
        home_recent = analysis.get('home_recent_games', [])
        away_recent = analysis.get('away_recent_games', [])

        if home_recent:
            high_scoring_games = sum(1 for g in home_recent
                                    if '-' in g.get('score', '') and
                                    sum(int(x) for x in g['score'].split('-')) > 220)
            if high_scoring_games >= 3:
                insights['deep_dive']['pace'] = f"{home_team['name']} 최근 고속 페이스 레짐 ({high_scoring_games}/5 경기 220+ 총점)"

        # 3. 수비 레짐 (실점 패턴)
        if home_allowed > 0:
            if home_allowed > 120:
                insights['risk_factors'].append(f"⚠️ {home_team['name']} 수비 붕괴 중 (평균 {home_allowed:.1f} 실점)")
            elif home_allowed < 100:
                insights['deep_dive']['defense_regime'] = f"{home_team['name']} 엘리트 수비 레짐 (평균 {home_allowed:.1f} 실점)"

        if away_allowed > 0:
            if away_allowed > 120:
                insights['risk_factors'].append(f"⚠️ {away_team['name']} 수비 붕괴 중 (평균 {away_allowed:.1f} 실점)")
            elif away_allowed < 100:
                insights['deep_dive']['defense_regime'] = f"{away_team['name']} 엘리트 수비 레짐 (평균 {away_allowed:.1f} 실점)"

        # 4. 전적 기반 위험 요소
        home_record = home_team.get('record', 'N/A')
        away_record = away_team.get('record', 'N/A')

        if home_record != 'N/A':
            wins, losses = map(int, home_record.split('-'))
            if losses > wins * 1.5:  # 패배가 승리의 1.5배 이상
                insights['risk_factors'].append(f"⚠️ {home_team['name']} 하락세 ({home_record} L10)")

        if away_record != 'N/A':
            wins, losses = map(int, away_record.split('-'))
            if losses > wins * 1.5:
                insights['risk_factors'].append(f"⚠️ {away_team['name']} 하락세 ({away_record} L10)")

        # 5. 시나리오 분석
        home_win_pct = float(home_team.get('win_pct', '0%').rstrip('%')) if home_team.get('win_pct') != 'N/A' else 0
        away_win_pct = float(away_team.get('win_pct', '0%').rstrip('%')) if away_team.get('win_pct') != 'N/A' else 0

        # 블로우아웃 시나리오
        if abs(home_win_pct - away_win_pct) >= 25:
            favorite = home_team['name'] if home_win_pct > away_win_pct else away_team['name']
            insights['scenarios']['blowout'] = f"{favorite} 블로우아웃 가능성 (전력 차이 {abs(home_win_pct - away_win_pct):.0f}%p)"

        # 클로즈 게임 시나리오
        if h2h:
            close_games = sum(1 for g in h2h
                            if g.get('home_score') and g.get('away_score') and
                            abs(g['home_score'] - g['away_score']) <= 5)
            if close_games >= 2:
                insights['scenarios']['close_game'] = f"클로즈 게임 예상 (H2H {close_games}/{len(h2h)} 경기가 5점차 이내)"

        # 복수전 시나리오
        if h2h and len(h2h) >= 3:
            recent_h2h = h2h[0]  # 가장 최근
            if recent_h2h.get('home_score') and recent_h2h.get('away_score'):
                last_winner = recent_h2h['home_team'] if recent_h2h['home_score'] > recent_h2h['away_score'] else recent_h2h['away_team']
                last_loser = recent_h2h['away_team'] if last_winner == recent_h2h['home_team'] else recent_h2h['home_team']

                current_home = analysis['home_team']['abbreviation']
                current_away = analysis['away_team']['abbreviation']

                if last_loser in [current_home, current_away]:
                    loser_name = home_team['name'] if last_loser == current_home else away_team['name']
                    insights['scenarios']['revenge'] = f"{loser_name} 복수전 동기 (최근 H2H 패배)"

        return insights

    def generate_narrative_analysis(self, analysis, insights):
        """OpenRouter LLM을 사용한 서사형 분석 생성"""
        if not self.openrouter_api_key:
            return None

        home = analysis['home_team']
        away = analysis['away_team']

        # 분석 데이터를 텍스트로 구성
        context = f"""
# {away['name']} @ {home['name']} 매치업 분석

## 팀 전력
홈팀 {home['name']}: {home.get('record', 'N/A')} ({home.get('win_pct', 'N/A')}), 평균 득점 {home.get('avg_scored', 'N/A')}, 평균 실점 {home.get('avg_allowed', 'N/A')}
원정팀 {away['name']}: {away.get('record', 'N/A')} ({away.get('win_pct', 'N/A')}), 평균 득점 {away.get('avg_scored', 'N/A')}, 평균 실점 {away.get('avg_allowed', 'N/A')}

## H2H & Form
- H2H: {insights.get('h2h_edge', 'Even')}
- 최근 폼: {insights.get('form_edge', 'Similar')}

## Deep Dive
"""
        deep_dive = insights.get('deep_dive', {})
        for key, value in deep_dive.items():
            context += f"- {value}\n"

        context += "\n## Risk Factors\n"
        for risk in insights.get('risk_factors', []):
            context += f"- {risk}\n"

        context += "\n## Scenarios\n"
        scenarios = insights.get('scenarios', {})
        for key, value in scenarios.items():
            context += f"- {value}\n"

        # LLM 프롬프트
        prompt = f"""당신은 NBA 베팅 분석 전문가입니다. 다음 데이터를 바탕으로 서사형 분석 리포트를 작성하세요.

{context}

요구사항:
1. 3-4개 문단으로 구성 (각 문단 3-5문장)
2. 스토리텔링 형식으로 핵심 인사이트를 풀어서 설명
3. "왜 이 팀이 유리한가?"에 대한 논리적 설명
4. 구체적인 숫자와 패턴을 언급하며 설득력 있게 작성
5. 마지막 문단은 예상 시나리오와 베팅 전략 제시
6. 한국어로 작성

분석:"""

        # OpenRouter API 호출 (xiaomi/mimo-v2-flash:free 먼저, 실패시 gpt-4o-mini)
        models = [
            "xiaomi/mimo-v2-flash:free",
            "openai/gpt-4o-mini"
        ]

        for model in models:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    narrative = result['choices'][0]['message']['content']
                    return narrative.strip()
                else:
                    print(f"  ⚠️ {model} failed: {response.status_code}")
                    continue

            except Exception as e:
                print(f"  ⚠️ {model} error: {e}")
                continue

        return None

    def generate_matchup_analysis(self, home_team, away_team, game_id=None, game_date=None):
        """매치업 분석 생성"""

        # 팀 정보
        home_info = self.get_team_info(home_team)
        away_info = self.get_team_info(away_team)

        if not home_info or not away_info:
            return None

        # H2H 기록
        h2h = self.get_h2h_history(home_team, away_team)

        # 최근 경기
        home_recent = self.get_recent_games(home_team, 5)
        away_recent = self.get_recent_games(away_team, 5)

        # 라인업 정보
        lineup_comparison = self.lineup_collector.get_lineup_comparison(home_team, away_team)

        # 주요 선수 (라인업 기반)
        home_lineup = lineup_comparison.get('home', {}).get('lineup', {})
        away_lineup = lineup_comparison.get('away', {}).get('lineup', {})

        home_players = self.get_key_players(home_team, home_lineup)
        away_players = self.get_key_players(away_team, away_lineup)

        # 심판 정보 (game_id가 있으면 해당 경기 심판, 없으면 오늘 심판)
        officials = self.referee_collector.get_todays_officials(game_date)
        referee_info = officials.get(game_id, officials.get('default', {})) if game_id else officials.get('default', {})

        # 주심 영향 분석
        crew_chief = referee_info.get('crew_chief', 'TBD')
        referee_impact = None
        if crew_chief != 'TBD':
            referee_impact = self.referee_collector.get_referee_impact_analysis(
                crew_chief, home_team, away_team
            )

        # Odds 데이터 수집
        odds_data = None
        if self.odds_adapter:
            try:
                all_odds = self.odds_adapter.get_nba_odds(markets=['h2h', 'spreads', 'totals'])
                if all_odds['success']:
                    # 팀 약자를 Odds API 풀네임으로 변환
                    home_full_name = self.TEAM_NAME_MAPPING.get(home_team, home_info['name'])
                    away_full_name = self.TEAM_NAME_MAPPING.get(away_team, away_info['name'])

                    # 매칭되는 게임 찾기
                    for game in all_odds['games']:
                        game_home = game.get('home_team', '')
                        game_away = game.get('away_team', '')

                        # 풀네임으로 정확히 매칭
                        if game_home == home_full_name and game_away == away_full_name:
                            odds_data = self.odds_adapter.extract_best_odds(game)
                            odds_data['commence_time'] = game.get('commence_time', 'TBD')
                            break
            except Exception as e:
                print(f"  ⚠️ Odds API 오류: {e}")

        return {
            'matchup': f"{away_team} @ {home_team}",
            'home_team': home_info,
            'away_team': away_info,
            'h2h_history': h2h,
            'home_recent_games': home_recent,
            'away_recent_games': away_recent,
            'home_key_players': home_players,
            'away_key_players': away_players,
            'lineup_comparison': lineup_comparison,
            'referee_info': referee_info,
            'referee_impact': referee_impact,
            'odds_data': odds_data
        }

    def generate_report_markdown(self, analysis):
        """마크다운 리포트 생성"""

        home = analysis['home_team']
        away = analysis['away_team']

        report = f"""# 🏀 G9 NBA Graph RAG Analysis Report

## {analysis['matchup']}
**{away['name']} @ {home['name']}**

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Data Source: VPS Neo4j (3,209 games, 2 seasons)

---

## 📊 Team Analysis

### {home['name']} (Home)
- **Recent Record (L10)**: {home.get('record', 'N/A')} ({home.get('win_pct', 'N/A')})
- **Avg Points Scored**: {home.get('avg_scored', 'N/A')}
- **Avg Points Allowed**: {home.get('avg_allowed', 'N/A')}

### {away['name']} (Away)
- **Recent Record (L10)**: {away.get('record', 'N/A')} ({away.get('win_pct', 'N/A')})
- **Avg Points Scored**: {away.get('avg_scored', 'N/A')}
- **Avg Points Allowed**: {away.get('avg_allowed', 'N/A')}

---

## 📜 Head-to-Head History

"""

        if analysis['h2h_history']:
            report += "최근 5경기 맞대결:\n\n"
            for game in analysis['h2h_history']:
                home_score = game['home_score'] if game['home_score'] else 'N/A'
                away_score = game['away_score'] if game['away_score'] else 'N/A'
                report += f"- **{game['date']}**: {game['away_team']} {away_score} @ {game['home_team']} {home_score}\n"
        else:
            report += "최근 맞대결 기록 없음\n"

        report += """
---

## 🔥 Recent Form

"""

        report += f"### {home['name']} (최근 5경기)\n\n"
        if analysis['home_recent_games']:
            for game in analysis['home_recent_games']:
                report += f"- **{game['date']}**: vs {game['opponent']} ({game['location']}) - {game['result']} ({game['score']})\n"
        else:
            report += "데이터 없음\n"

        report += f"\n### {away['name']} (최근 5경기)\n\n"
        if analysis['away_recent_games']:
            for game in analysis['away_recent_games']:
                report += f"- **{game['date']}**: vs {game['opponent']} ({game['location']}) - {game['result']} ({game['score']})\n"
        else:
            report += "데이터 없음\n"

        report += """
---

## 👥 Key Players

"""

        report += f"### {home['name']}\n\n"
        if analysis['home_key_players']:
            for player in analysis['home_key_players']:
                pos = player.get('position', 'N/A')
                report += f"- **{player['name']}** ({pos})\n"
        else:
            report += "선수 데이터 없음\n"

        report += f"\n### {away['name']}\n\n"
        if analysis['away_key_players']:
            for player in analysis['away_key_players']:
                pos = player.get('position', 'N/A')
                report += f"- **{player['name']}** ({pos})\n"
        else:
            report += "선수 데이터 없음\n"

        # 라인업 정보 추가
        report += """
---

## 🏃 Expected Lineups

"""
        lineup_comp = analysis.get('lineup_comparison', {})

        # Home 라인업
        report += f"### {home['name']} (Home)\n\n"
        home_lineup = lineup_comp.get('home', {}).get('lineup', {})
        if home_lineup.get('starters'):
            for starter in home_lineup['starters']:
                name = starter.get('name', 'TBD')
                pos = starter.get('position', 'N/A')
                report += f"- **{pos}**: {name}\n"
            report += f"\n**Source**: {home_lineup.get('source', 'N/A')}\n"
            report += f"**Confidence**: {home_lineup.get('confidence', 'N/A')}\n"
        else:
            report += "라인업 정보 없음 (경기 30분 전 확인 필요)\n"

        # Away 라인업
        report += f"\n### {away['name']} (Away)\n\n"
        away_lineup = lineup_comp.get('away', {}).get('lineup', {})
        if away_lineup.get('starters'):
            for starter in away_lineup['starters']:
                name = starter.get('name', 'TBD')
                pos = starter.get('position', 'N/A')
                report += f"- **{pos}**: {name}\n"
            report += f"\n**Source**: {away_lineup.get('source', 'N/A')}\n"
            report += f"**Confidence**: {away_lineup.get('confidence', 'N/A')}\n"
        else:
            report += "라인업 정보 없음 (경기 30분 전 확인 필요)\n"

        # 심판 정보 추가
        report += """
---

## 👨‍⚖️ Officials & Referee Analysis

"""
        referee_info = analysis.get('referee_info', {})
        if referee_info and referee_info.get('crew_chief') != 'TBD':
            report += f"**Crew Chief**: {referee_info.get('crew_chief', 'TBD')}\n"

            referees = referee_info.get('referees', [])
            if referees and referees != ['TBD', 'TBD', 'TBD']:
                report += "\n**Officials**:\n"
                for ref in referees:
                    report += f"- {ref}\n"

            # 심판 영향 분석
            referee_impact = analysis.get('referee_impact')
            if referee_impact:
                report += f"\n**Strictness Index**: {referee_impact.get('strictness', 0.65):.2f} (0=관대, 1=엄격)\n"
                report += f"**Expected Fouls**: {referee_impact.get('expected_fouls', 'N/A')}\n"
                report += f"**Impact**: {referee_impact.get('impact', 'NEUTRAL')}\n"
                report += f"\n*{referee_impact.get('note', '')}*\n"
                report += f"\n**Betting Impact**: {referee_impact.get('betting_impact', 'N/A')}\n"
        else:
            report += "심판 정보: TBD (경기 30분 전 @OfficialNBARefs 확인)\n"

        # Odds 정보 추가
        report += """
---

## 💰 Betting Odds & Lines

"""
        odds_data = analysis.get('odds_data')
        if odds_data:
            # Moneyline (h2h)
            if 'h2h' in odds_data:
                h2h = odds_data['h2h']
                report += "### Moneyline\n\n"
                if 'home' in h2h:
                    report += f"- **{home['name']}**: {h2h['home']['odds']:+d} ({h2h['home']['bookmaker']})\n"
                if 'away' in h2h:
                    report += f"- **{away['name']}**: {h2h['away']['odds']:+d} ({h2h['away']['bookmaker']})\n"
                report += "\n"

            # Spreads
            if 'spreads' in odds_data:
                spreads = odds_data['spreads']
                report += "### Point Spread\n\n"
                if 'home' in spreads:
                    point = spreads['home'].get('point', 0)
                    odds = spreads['home']['odds']
                    report += f"- **{home['name']}**: {point:+.1f} ({odds:+d}) - {spreads['home']['bookmaker']}\n"
                if 'away' in spreads:
                    point = spreads['away'].get('point', 0)
                    odds = spreads['away']['odds']
                    report += f"- **{away['name']}**: {point:+.1f} ({odds:+d}) - {spreads['away']['bookmaker']}\n"
                report += "\n"

            # Totals
            if 'totals' in odds_data:
                totals = odds_data['totals']
                report += "### Over/Under\n\n"
                if 'over' in totals:
                    point = totals['over'].get('point', 0)
                    odds = totals['over']['odds']
                    report += f"- **Over {point}**: {odds:+d} ({totals['over']['bookmaker']})\n"
                if 'under' in totals:
                    point = totals['under'].get('point', 0)
                    odds = totals['under']['odds']
                    report += f"- **Under {point}**: {odds:+d} ({totals['under']['bookmaker']})\n"
                report += "\n"

            # Game time
            if odds_data.get('commence_time'):
                report += f"**Game Time**: {odds_data['commence_time']}\n"
        else:
            report += "배팅 오즈 정보 없음 (The Odds API 호출 필요)\n"

        # AI 인사이트 섹션 추가
        report += """
---

## 🧠 Matchup Analysis & Betting Insights

"""
        insights = self.analyze_matchup_insights(analysis)

        # H2H Edge
        if insights['h2h_edge']:
            report += f"**Head-to-Head Edge**: {insights['h2h_edge']}\n\n"

        # Form Edge
        if insights['form_edge']:
            report += f"**Current Form**: {insights['form_edge']}\n\n"

        # Spread Analysis
        if insights['spread_analysis']:
            report += f"**Spread Analysis**: {insights['spread_analysis']}\n\n"

        # Total Analysis
        if insights['total_analysis']:
            report += f"**Total Analysis**: {insights['total_analysis']}\n\n"

        # === Narrative 분석 (서사형) ===
        narrative = self.generate_narrative_analysis(analysis, insights)
        if narrative:
            report += "---\n\n## 📖 Narrative Analysis\n\n"
            report += f"{narrative}\n\n"

        # === Deep Dive 분석 ===
        deep_dive = insights.get('deep_dive', {})
        if deep_dive:
            report += "---\n\n## 🔍 Deep Dive Analysis\n\n"

            if 'home_offense_edge' in deep_dive:
                report += f"**홈 공격 우위**: {deep_dive['home_offense_edge']}\n\n"

            if 'away_offense_edge' in deep_dive:
                report += f"**원정 공격 우위**: {deep_dive['away_offense_edge']}\n\n"

            if 'defense_regime' in deep_dive:
                report += f"**수비 레짐**: {deep_dive['defense_regime']}\n\n"

            if 'pace' in deep_dive:
                report += f"**페이스 트렌드**: {deep_dive['pace']}\n\n"

        # === Risk Factors ===
        risk_factors = insights.get('risk_factors', [])
        if risk_factors:
            report += "---\n\n## ⚠️ Risk Factors\n\n"
            for risk in risk_factors:
                report += f"{risk}\n\n"

        # === Scenarios ===
        scenarios = insights.get('scenarios', {})
        if scenarios:
            report += "---\n\n## 📈 Possible Scenarios\n\n"

            if 'blowout' in scenarios:
                report += f"**블로우아웃 시나리오**: {scenarios['blowout']}\n\n"

            if 'close_game' in scenarios:
                report += f"**클로즈 게임**: {scenarios['close_game']}\n\n"

            if 'revenge' in scenarios:
                report += f"**복수전**: {scenarios['revenge']}\n\n"

        report += "---\n\n"

        # 종합 추천
        report += "**Betting Recommendation**:\n\n"

        has_recommendation = False
        h2h_edge = insights.get('h2h_edge', '')
        form_edge = insights.get('form_edge', '')

        # Moneyline 추천 (Odds 유무와 관계없이)
        odds_data = analysis.get('odds_data')

        # 양쪽 모두 같은 팀 추천
        if h2h_edge and form_edge:
            if analysis['home_team']['name'] in h2h_edge and analysis['home_team']['name'] in form_edge:
                if odds_data and 'h2h' in odds_data:
                    home_ml = odds_data['h2h'].get('home', {}).get('odds', 0)
                    report += f"- **Moneyline**: {home['name']} ({home_ml:+d}) - Strong H2H + Form advantage\n"
                else:
                    report += f"- **Lean**: {home['name']} - Strong H2H + Form advantage\n"
                has_recommendation = True
            elif analysis['away_team']['name'] in h2h_edge and analysis['away_team']['name'] in form_edge:
                if odds_data and 'h2h' in odds_data:
                    away_ml = odds_data['h2h'].get('away', {}).get('odds', 0)
                    report += f"- **Moneyline**: {away['name']} ({away_ml:+d}) - Strong H2H + Form advantage\n"
                else:
                    report += f"- **Lean**: {away['name']} - Strong H2H + Form advantage\n"
                has_recommendation = True
        # H2H만 있어도 추천
        elif h2h_edge and 'dominates' in h2h_edge:
            if analysis['home_team']['name'] in h2h_edge:
                if odds_data and 'h2h' in odds_data:
                    home_ml = odds_data['h2h'].get('home', {}).get('odds', 0)
                    report += f"- **Moneyline**: {home['name']} ({home_ml:+d}) - H2H advantage\n"
                else:
                    report += f"- **Lean**: {home['name']} - H2H advantage\n"
                has_recommendation = True
            elif analysis['away_team']['name'] in h2h_edge:
                if odds_data and 'h2h' in odds_data:
                    away_ml = odds_data['h2h'].get('away', {}).get('odds', 0)
                    report += f"- **Moneyline**: {away['name']} ({away_ml:+d}) - H2H advantage\n"
                else:
                    report += f"- **Lean**: {away['name']} - H2H advantage\n"
                has_recommendation = True

        # Spread 추천
        if insights.get('spread_analysis'):
            report += f"- **Spread**: {insights['spread_analysis']}\n"
            has_recommendation = True

        # Total 추천
        if insights.get('total_analysis'):
            report += f"- **Total**: {insights['total_analysis']}\n"
            has_recommendation = True

        # Key Factors
        if insights.get('key_factors'):
            report += f"\n**Key Trends**:\n"
            for factor in insights['key_factors']:
                report += f"- {factor}\n"
            has_recommendation = True

        if not has_recommendation:
            report += "- Insufficient edge identified. Monitor lineups 30 min before tipoff for injury updates.\n"

        report += """
---

## 💡 Graph RAG Insights

**Data Sources**:
- VPS Neo4j (1,887 games, 15,433 nodes)
- H2H History
- Recent Form Tracking
- Key Player Information
- Expected Lineups (3-stage fallback)
- Referee Stats & Impact Analysis
- The Odds API (Moneyline, Spreads, Totals)

**Note**: 부상자 정보는 경기 시작 전 별도 확인 필요합니다.
라인업과 심판은 경기 30분 전 최종 확인을 권장합니다.
배팅 오즈는 실시간으로 변동될 수 있습니다.

---

**© 2025 G9 Regime Zero - Graph RAG Based Analysis**
**Generated from VPS Neo4j Database**
"""

        return report


def main():
    """메인 실행"""

    # 내일 경기 로드
    try:
        with open('/Users/js/g9/nba_data/odds_report_engine/tomorrows_games.json', 'r') as f:
            games = json.load(f)
    except FileNotFoundError:
        print("❌ tomorrows_games.json 파일이 없습니다.")
        sys.exit(1)

    print(f"=== G9 Graph RAG Report Generator ===")
    print(f"내일 경기: {len(games)}경기\n")

    generator = GraphRAGReportGenerator()

    output_dir = '/Users/js/g9/nba_data/odds_reports/'

    for i, game in enumerate(games, 1):
        home_team = game['home_team']
        away_team = game['away_team']
        game_id = game.get('game_id')
        game_date = game.get('date', '').split('T')[0].replace('-', '') if game.get('date') else None

        print(f"[{i}/{len(games)}] {away_team} @ {home_team} 분석 중...")

        try:
            # 매치업 분석 (game_id와 date 전달)
            analysis = generator.generate_matchup_analysis(
                home_team, away_team,
                game_id=game_id,
                game_date=game_date
            )

            if not analysis:
                print(f"  ⚠️ 팀 데이터를 찾을 수 없습니다.")
                continue

            # 리포트 생성
            report = generator.generate_report_markdown(analysis)

            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{output_dir}graphrag_{away_team}_at_{home_team}_{timestamp}.md"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            print(f"  ✅ 리포트 저장: {filename}")

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            continue

    generator.close()
    print(f"\n✅ 모든 리포트 생성 완료!")


if __name__ == "__main__":
    main()
