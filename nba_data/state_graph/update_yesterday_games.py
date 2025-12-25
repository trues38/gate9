#!/usr/bin/env python3
"""
어제 경기 결과를 Neo4j에 자동 추가 (v2.0)
- GameState (팀 수준)
- PlayerBoxScore (선수 수준, 25-26 시즌만)

매일 한 번 실행하면 최신 데이터 유지
"""

import requests
from datetime import datetime, timedelta
from neo4j import GraphDatabase
from typing import Dict, Optional, List
import json
import time

class DailyUpdater:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_yesterday_date(self) -> str:
        """어제 날짜 YYYYMMDD 형식"""
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime("%Y%m%d")

    def fetch_games(self, date: str) -> List[Dict]:
        """ESPN API에서 특정 날짜 경기 결과 가져오기"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for event in data.get('events', []):
                competition = event['competitions'][0]

                # 경기 완료된 것만
                if competition['status']['type']['state'] != 'post':
                    continue

                games.append({
                    'game_id': event['id'],
                    'date': event['date'][:10],  # YYYY-MM-DD
                    'home_team': competition['competitors'][0]['team']['abbreviation'],
                    'away_team': competition['competitors'][1]['team']['abbreviation'],
                    'home_score': int(competition['competitors'][0]['score']),
                    'away_score': int(competition['competitors'][1]['score']),
                    'home_win': int(competition['competitors'][0]['score']) > int(competition['competitors'][1]['score']),
                    'status': competition['status']['type']['state']
                })

            return games

        except Exception as e:
            print(f"❌ API 오류: {e}")
            return []

    def calculate_rest_days(self, team: str, game_date: str) -> int:
        """팀의 휴식일 계산 (Neo4j에서 마지막 경기 조회)"""
        query = """
        MATCH (game:GameState)
        WHERE (game.home_team = $team OR game.away_team = $team)
          AND game.date < date($game_date)
        RETURN game.date AS last_game_date
        ORDER BY game.date DESC
        LIMIT 1
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, game_date=game_date)
            record = result.single()

            if not record:
                return 7  # 첫 경기

            last_date = record['last_game_date']
            game_dt = datetime.strptime(game_date, "%Y-%m-%d")
            last_dt = datetime.strptime(str(last_date), "%Y-%m-%d")

            rest_days = (game_dt - last_dt).days - 1
            return max(0, rest_days)

    def fetch_boxscore(self, game_id: str) -> Optional[Dict]:
        """경기의 box score 가져오기 (25-26 시즌만)"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'boxscore' not in data or 'players' not in data['boxscore']:
                return None

            return data['boxscore']['players']
        except Exception as e:
            print(f"      ⚠️  Box score 수집 실패: {e}")
            return None

    def parse_stat_value(self, value: str, stat_name: str):
        """스탯 값 파싱"""
        if value == 'DNP' or value == 'N/A' or value == '':
            return None

        if '-' in value and stat_name in ['FG', '3PT', 'FT']:
            parts = value.split('-')
            return {
                'made': int(parts[0]) if parts[0].isdigit() else 0,
                'attempted': int(parts[1]) if parts[1].isdigit() else 0
            }

        try:
            if stat_name == '+/-':
                return int(value.replace('+', ''))
            return int(value)
        except ValueError:
            return value

    def add_player_boxscores(self, game_id: str, game_date: str):
        """선수 box score를 Neo4j에 추가 (25-26 시즌만)"""
        game_dt = datetime.strptime(game_date, "%Y-%m-%d")

        if game_dt < datetime(2025, 10, 1):
            return 0

        players_data = self.fetch_boxscore(game_id)
        if not players_data:
            return 0

        imported = 0

        for team_data in players_data:
            team = team_data['team']['abbreviation']

            if not team_data.get('statistics'):
                continue

            stats_cat = team_data['statistics'][0]
            labels = stats_cat.get('labels', [])

            for athlete_data in stats_cat.get('athletes', []):
                athlete = athlete_data['athlete']
                stats = athlete_data['stats']

                fg = self.parse_stat_value(stats[labels.index('FG')] if 'FG' in labels else '0-0', 'FG')
                three_pt = self.parse_stat_value(stats[labels.index('3PT')] if '3PT' in labels else '0-0', '3PT')
                ft = self.parse_stat_value(stats[labels.index('FT')] if 'FT' in labels else '0-0', 'FT')

                with self.driver.session() as session:
                    session.run("""
                        MERGE (pb:PlayerBoxScore {game_id: $game_id, player_id: $player_id})
                        SET pb.player_name = $player_name,
                            pb.team = $team,
                            pb.position = $position,
                            pb.date = date($date),
                            pb.minutes = $minutes,
                            pb.points = $points,
                            pb.rebounds = $rebounds,
                            pb.assists = $assists,
                            pb.steals = $steals,
                            pb.blocks = $blocks,
                            pb.turnovers = $turnovers,
                            pb.fouls = $fouls,
                            pb.plus_minus = $plus_minus,
                            pb.fg_made = $fg_made,
                            pb.fg_attempted = $fg_attempted,
                            pb.three_made = $three_made,
                            pb.three_attempted = $three_attempted,
                            pb.ft_made = $ft_made,
                            pb.ft_attempted = $ft_attempted,
                            pb.off_rebounds = $off_rebounds,
                            pb.def_rebounds = $def_rebounds

                        WITH pb
                        MATCH (g:GameState {game_id: $game_id})
                        MERGE (g)-[:HAS_BOXSCORE]->(pb)

                        WITH pb
                        MERGE (p:Player {name: $player_name})
                        MERGE (p)-[:PLAYED_IN]->(pb)
                    """,
                        game_id=game_id,
                        player_id=athlete['id'],
                        player_name=athlete['displayName'],
                        team=team,
                        position=athlete.get('position', {}).get('abbreviation', 'N/A'),
                        date=game_date,
                        minutes=self.parse_stat_value(stats[labels.index('MIN')] if 'MIN' in labels else '0', 'MIN'),
                        points=self.parse_stat_value(stats[labels.index('PTS')] if 'PTS' in labels else '0', 'PTS'),
                        rebounds=self.parse_stat_value(stats[labels.index('REB')] if 'REB' in labels else '0', 'REB'),
                        assists=self.parse_stat_value(stats[labels.index('AST')] if 'AST' in labels else '0', 'AST'),
                        steals=self.parse_stat_value(stats[labels.index('STL')] if 'STL' in labels else '0', 'STL'),
                        blocks=self.parse_stat_value(stats[labels.index('BLK')] if 'BLK' in labels else '0', 'BLK'),
                        turnovers=self.parse_stat_value(stats[labels.index('TO')] if 'TO' in labels else '0', 'TO'),
                        fouls=self.parse_stat_value(stats[labels.index('PF')] if 'PF' in labels else '0', 'PF'),
                        plus_minus=self.parse_stat_value(stats[labels.index('+/-')] if '+/-' in labels else '0', '+/-'),
                        fg_made=fg['made'] if fg else 0,
                        fg_attempted=fg['attempted'] if fg else 0,
                        three_made=three_pt['made'] if three_pt else 0,
                        three_attempted=three_pt['attempted'] if three_pt else 0,
                        ft_made=ft['made'] if ft else 0,
                        ft_attempted=ft['attempted'] if ft else 0,
                        off_rebounds=self.parse_stat_value(stats[labels.index('OREB')] if 'OREB' in labels else '0', 'OREB'),
                        def_rebounds=self.parse_stat_value(stats[labels.index('DREB')] if 'DREB' in labels else '0', 'DREB')
                    )

                    imported += 1

        return imported

    def add_game_to_neo4j(self, game: Dict):
        """경기 결과를 Neo4j에 추가"""
        # 휴식일 계산
        home_rest = self.calculate_rest_days(game['home_team'], game['date'])
        away_rest = self.calculate_rest_days(game['away_team'], game['date'])

        query = """
        MERGE (game:GameState {game_id: $game_id})
        SET game.date = date($date),
            game.home_team = $home_team,
            game.away_team = $away_team,
            game.home_score = $home_score,
            game.away_score = $away_score,
            game.home_win = $home_win,
            game.home_rest_days = $home_rest_days,
            game.away_rest_days = $away_rest_days,
            game.updated_at = datetime()

        MERGE (home:Team {abbr: $home_team})
        MERGE (away:Team {abbr: $away_team})

        MERGE (game)-[:HOME_TEAM]->(home)
        MERGE (game)-[:AWAY_TEAM]->(away)
        """

        with self.driver.session() as session:
            session.run(query,
                game_id=game['game_id'],
                date=game['date'],
                home_team=game['home_team'],
                away_team=game['away_team'],
                home_score=game['home_score'],
                away_score=game['away_score'],
                home_win=game['home_win'],
                home_rest_days=home_rest,
                away_rest_days=away_rest
            )

        time.sleep(0.5)
        player_count = self.add_player_boxscores(game['game_id'], game['date'])
        return player_count

    def update_yesterday(self):
        """어제 경기 결과 업데이트"""
        yesterday = self.get_yesterday_date()
        yesterday_display = datetime.now() - timedelta(days=1)

        print(f"📅 어제 경기 업데이트: {yesterday_display.strftime('%Y-%m-%d')}")
        print("=" * 70)

        # 경기 결과 가져오기
        games = self.fetch_games(yesterday)

        if not games:
            print("⚠️  어제 경기가 없거나 아직 종료되지 않았습니다.")
            return

        print(f"✅ {len(games)}개 경기 발견\n")

        # Neo4j에 추가
        added = 0
        total_players = 0
        for game in games:
            try:
                player_count = self.add_game_to_neo4j(game)
                result = "승" if game['home_win'] else "패"
                print(f"  ✓ {game['away_team']} @ {game['home_team']}: "
                      f"{game['away_score']}-{game['home_score']} ({result})", end='')
                if player_count > 0:
                    print(f" + {player_count}명 box score")
                    total_players += player_count
                else:
                    print()
                added += 1
            except Exception as e:
                print(f"  ✗ {game['game_id']} 추가 실패: {e}")

        print(f"\n{'=' * 70}")
        print(f"✅ {added}/{len(games)}개 경기 Neo4j 업데이트 완료")
        if total_players > 0:
            print(f"✅ {total_players}명 선수 box score 추가 (25-26 시즌)")
        print(f"💡 이제 최신 패턴이 내일 분석에 자동 반영됩니다.\n")

def main():
    updater = DailyUpdater()

    try:
        updater.update_yesterday()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        updater.close()

if __name__ == "__main__":
    main()
