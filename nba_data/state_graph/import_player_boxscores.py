#!/usr/bin/env python3
"""
25-26 시즌 선수 box score를 Neo4j에 임포트

스키마:
  (:PlayerBoxScore) - 선수별 경기 스탯
  (:GameState)-[:HAS_BOXSCORE]->(:PlayerBoxScore)
  (:Player)-[:PLAYED_IN]->(:PlayerBoxScore)
"""

import json
from pathlib import Path
from neo4j import GraphDatabase
from typing import Dict, List

class PlayerBoxScoreImporter:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_schema(self):
        """PlayerBoxScore 스키마 생성"""
        with self.driver.session() as session:
            # Constraint 생성 (game_id + player_id 조합으로 유니크)
            session.run("""
                CREATE CONSTRAINT player_boxscore_unique IF NOT EXISTS
                FOR (pb:PlayerBoxScore)
                REQUIRE (pb.game_id, pb.player_id) IS UNIQUE
            """)

            # Index 생성
            session.run("""
                CREATE INDEX player_boxscore_player_id IF NOT EXISTS
                FOR (pb:PlayerBoxScore) ON (pb.player_id)
            """)

            session.run("""
                CREATE INDEX player_boxscore_team IF NOT EXISTS
                FOR (pb:PlayerBoxScore) ON (pb.team)
            """)

            print("✅ PlayerBoxScore 스키마 생성 완료")

    def parse_stat_value(self, value: str, stat_name: str):
        """스탯 값을 파싱"""
        if value == 'DNP' or value == 'N/A' or value == '':
            return None

        # 슈팅 스탯 (FG, 3PT, FT)은 "7-14" 형식
        if '-' in value and stat_name in ['FG', '3PT', 'FT']:
            parts = value.split('-')
            return {
                'made': int(parts[0]) if parts[0].isdigit() else 0,
                'attempted': int(parts[1]) if parts[1].isdigit() else 0
            }

        # 숫자형
        try:
            # +/- 는 부호 포함
            if stat_name == '+/-':
                return int(value.replace('+', ''))
            return int(value)
        except ValueError:
            return value

    def import_boxscore_file(self, filepath: Path):
        """단일 box score 파일 임포트"""
        with open(filepath) as f:
            games = json.load(f)

        imported_players = 0

        for game in games:
            game_id = game['game_id']
            game_date = game['date']

            for team_data in game['teams']:
                team = team_data['team']

                for player in team_data['players']:
                    # 스탯 파싱
                    stats = player['stats']

                    # FG, 3PT, FT 파싱
                    fg = self.parse_stat_value(stats.get('FG', '0-0'), 'FG')
                    three_pt = self.parse_stat_value(stats.get('3PT', '0-0'), '3PT')
                    ft = self.parse_stat_value(stats.get('FT', '0-0'), 'FT')

                    # PlayerBoxScore 노드 생성
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
                            player_id=player['player_id'],
                            player_name=player['name'],
                            team=team,
                            position=player['position'],
                            date=game_date,
                            minutes=self.parse_stat_value(stats.get('MIN', '0'), 'MIN'),
                            points=self.parse_stat_value(stats.get('PTS', '0'), 'PTS'),
                            rebounds=self.parse_stat_value(stats.get('REB', '0'), 'REB'),
                            assists=self.parse_stat_value(stats.get('AST', '0'), 'AST'),
                            steals=self.parse_stat_value(stats.get('STL', '0'), 'STL'),
                            blocks=self.parse_stat_value(stats.get('BLK', '0'), 'BLK'),
                            turnovers=self.parse_stat_value(stats.get('TO', '0'), 'TO'),
                            fouls=self.parse_stat_value(stats.get('PF', '0'), 'PF'),
                            plus_minus=self.parse_stat_value(stats.get('+/-', '0'), '+/-'),
                            fg_made=fg['made'] if fg else 0,
                            fg_attempted=fg['attempted'] if fg else 0,
                            three_made=three_pt['made'] if three_pt else 0,
                            three_attempted=three_pt['attempted'] if three_pt else 0,
                            ft_made=ft['made'] if ft else 0,
                            ft_attempted=ft['attempted'] if ft else 0,
                            off_rebounds=self.parse_stat_value(stats.get('OREB', '0'), 'OREB'),
                            def_rebounds=self.parse_stat_value(stats.get('DREB', '0'), 'DREB')
                        )

                        imported_players += 1

        return imported_players

    def import_all_boxscores(self, boxscore_dir="player_boxscores_2025_26"):
        """모든 box score 파일 임포트"""
        boxscore_path = Path(boxscore_dir)

        if not boxscore_path.exists():
            print(f"❌ 디렉토리 없음: {boxscore_dir}")
            return

        files = sorted(boxscore_path.glob("boxscores_*.json"))

        if not files:
            print(f"❌ box score 파일 없음: {boxscore_dir}/")
            return

        print(f"\n📁 찾은 파일: {len(files)}개")
        print(f"{'='*80}\n")

        total_players = 0

        for filepath in files:
            print(f"📄 {filepath.name} 임포트 중... ", end='', flush=True)

            try:
                count = self.import_boxscore_file(filepath)
                total_players += count
                print(f"✅ ({count}명)")
            except Exception as e:
                print(f"❌ 오류: {e}")

        print(f"\n{'='*80}")
        print(f"✅ 임포트 완료!")
        print(f"{'='*80}")
        print(f"총 선수 기록: {total_players}개")
        print()

def main():
    import argparse

    parser = argparse.ArgumentParser(description='25-26 시즌 Box Score 임포터')
    parser.add_argument('--boxscore-dir', default='player_boxscores_2025_26', help='Box score 디렉토리')
    parser.add_argument('--create-schema', action='store_true', help='스키마 생성')

    args = parser.parse_args()

    print("=" * 80)
    print("25-26 시즌 선수 Box Score 임포터")
    print("=" * 80)

    importer = PlayerBoxScoreImporter()

    try:
        if args.create_schema:
            print("\n📋 스키마 생성 중...")
            importer.create_schema()

        print(f"\n📥 Box score 임포트 시작...")
        print(f"디렉토리: {args.boxscore_dir}/")

        importer.import_all_boxscores(args.boxscore_dir)

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()

if __name__ == "__main__":
    main()
