#!/usr/bin/env python3
"""
2023-24 시즌 데이터를 Neo4j에 임포트
기존 24-25 데이터와 병합
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from datetime import datetime

class SeasonImporter:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.season_dir = Path("/Users/js/g9/nba_data/state_graph/season_2023_24")

    def close(self):
        self.driver.close()

    def parse_game(self, event: Dict) -> Optional[Dict]:
        """ESPN API 경기 데이터 파싱"""
        try:
            competition = event['competitions'][0]
            status = competition['status']['type']['state']

            # 완료된 경기만
            if status != 'post':
                return None

            game_id = event['id']
            date = event['date'][:10]  # YYYY-MM-DD

            competitors = competition['competitors']
            home_team = next(c for c in competitors if c['homeAway'] == 'home')
            away_team = next(c for c in competitors if c['homeAway'] == 'away')

            home_score = int(home_team['score'])
            away_score = int(away_team['score'])

            game_data = {
                'game_id': game_id,
                'date': date,
                'home_team': home_team['team']['abbreviation'],
                'away_team': away_team['team']['abbreviation'],
                'home_score': home_score,
                'away_score': away_score,
                'home_win': home_score > away_score
            }

            return game_data

        except Exception as e:
            print(f"  ⚠️  파싱 실패: {e}")
            return None

    def calculate_rest_days(self, team: str, game_date: str) -> int:
        """팀의 휴식일 계산"""
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

    def import_game(self, game: Dict):
        """경기를 Neo4j에 임포트"""
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
            game.season = '2023-24',
            game.imported_at = datetime()

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

    def import_season(self):
        """시즌 전체 임포트"""
        print("=" * 80)
        print("2023-24 시즌 데이터 Neo4j 임포트")
        print("=" * 80)

        # JSON 파일 목록
        json_files = sorted(self.season_dir.glob("games_*.json"))

        if not json_files:
            print(f"\n❌ {self.season_dir}에 파일이 없습니다.")
            print("먼저 crawl_season_2023_24.py를 실행하세요.")
            return

        print(f"\n총 {len(json_files)}개 파일 발견")
        print("임포트 시작...\n")

        total_games = 0
        imported_games = 0
        failed_games = 0

        for i, filepath in enumerate(json_files, 1):
            date = filepath.stem.replace('games_', '')

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            games = data.get('events', [])

            if not games:
                continue

            print(f"[{i}/{len(json_files)}] {date[:4]}-{date[4:6]}-{date[6:8]}: {len(games)}경기", end=" ")

            for event in games:
                total_games += 1
                game = self.parse_game(event)

                if game:
                    try:
                        self.import_game(game)
                        imported_games += 1
                    except Exception as e:
                        failed_games += 1
                        print(f"\n  ❌ {game['game_id']} 임포트 실패: {e}")

            print("✅")

            # 진행률 표시
            if i % 30 == 0:
                print(f"\n진행률: {i/len(json_files)*100:.1f}% | 임포트: {imported_games}개\n")

        # 결과 요약
        print("\n" + "=" * 80)
        print("임포트 완료!")
        print("=" * 80)
        print(f"\n총 경기: {total_games}개")
        print(f"임포트 성공: {imported_games}개")
        print(f"임포트 실패: {failed_games}개")

        # Neo4j 통계 확인
        self.print_neo4j_stats()

    def print_neo4j_stats(self):
        """Neo4j 통계 출력"""
        query = """
        MATCH (g:GameState)
        WITH count(*) AS total_games,
             min(g.date) AS earliest,
             max(g.date) AS latest
        RETURN total_games, earliest, latest
        """

        with self.driver.session() as session:
            result = session.run(query)
            record = result.single()

            print(f"\n📊 Neo4j 전체 통계:")
            print(f"   총 경기: {record['total_games']}개")
            print(f"   기간: {record['earliest']} ~ {record['latest']}")

        # 시즌별 분포
        query_season = """
        MATCH (g:GameState)
        WITH substring(toString(g.date), 0, 4) AS year,
             count(*) AS games
        RETURN year, games
        ORDER BY year DESC
        """

        with self.driver.session() as session:
            result = session.run(query_season)
            records = list(result)

            print(f"\n   시즌별 분포:")
            for record in records:
                print(f"   {record['year']}년: {record['games']}경기")

def main():
    importer = SeasonImporter()

    try:
        importer.import_season()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()

if __name__ == "__main__":
    main()
