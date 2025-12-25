"""
Neo4j 마이그레이션 - Clean Version
===================================
927게임 전체를 깨끗한 Schema로 임포트

Made with ❤️ by State Graph Engine
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from datetime import datetime
from collections import defaultdict


# ============================================================================
# Neo4j 연결
# ============================================================================

class CleanMigration:
    """깨끗한 마이그레이션"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.stats = defaultdict(int)
        print(f"✅ Neo4j 연결: {uri}")

    def close(self):
        self.driver.close()

    # ========================================================================
    # Step 1: Constraints & Indexes
    # ========================================================================

    def create_constraints(self):
        """Constraints 및 Indexes 생성"""
        print("\n" + "=" * 70)
        print("Step 1: Constraints & Indexes")
        print("=" * 70)

        with self.driver.session() as session:
            commands = [
                "CREATE CONSTRAINT team_abbr IF NOT EXISTS FOR (t:Team) REQUIRE t.abbr IS UNIQUE",
                "CREATE CONSTRAINT player_name IF NOT EXISTS FOR (p:Player) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT referee_name IF NOT EXISTS FOR (r:Referee) REQUIRE r.name IS UNIQUE",
                "CREATE CONSTRAINT venue_id IF NOT EXISTS FOR (v:Venue) REQUIRE v.id IS UNIQUE",
                "CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:GameState) REQUIRE g.game_id IS UNIQUE",
                "CREATE INDEX game_date IF NOT EXISTS FOR (g:GameState) ON (g.date)",
                "CREATE INDEX game_season IF NOT EXISTS FOR (g:GameState) ON (g.season)",
            ]

            for cmd in commands:
                try:
                    session.run(cmd)
                    name = cmd.split()[2]
                    print(f"  ✅ {name}")
                except Exception as e:
                    print(f"  ⚠️  {cmd.split()[2]}: {str(e)[:50]}")

    # ========================================================================
    # Step 2: 데이터 로드
    # ========================================================================

    def load_games(self, limit: Optional[int] = None) -> List[Dict]:
        """raw/ 디렉토리에서 게임 로드"""
        print("\n" + "=" * 70)
        print(f"Step 2: 게임 데이터 로드 {f'(최대 {limit}개)' if limit else ''}")
        print("=" * 70)

        raw_path = Path("raw")
        game_files = sorted(raw_path.glob("*_game_*.json"))

        if limit:
            game_files = game_files[:limit]

        games = []
        for file_path in game_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    game_id = file_path.stem.split('_game_')[1]
                    games.append({'game_id': game_id, 'data': data})
            except Exception as e:
                print(f"  ⚠️  {file_path.name}: {e}")

        print(f"  ✅ {len(games)}개 게임 로드")
        return games

    def load_snapshots(self) -> Dict:
        """snapshots/ 디렉토리에서 컨텍스트 로드"""
        print("\n  snapshots에서 컨텍스트 로드 중...")

        snapshots_path = Path("snapshots")
        snapshot_files = list(snapshots_path.glob("*.json"))

        game_contexts = {}
        for file_path in snapshot_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for game in data:
                        game_id = game.get('game_id')
                        if game_id:
                            game_contexts[game_id] = {
                                'home_rest_days': game.get('home_team', {}).get('rest_days', 0),
                                'away_rest_days': game.get('away_team', {}).get('rest_days', 0),
                                'referees': game.get('referees', [])
                            }
            except Exception as e:
                pass  # 조용히 스킵

        print(f"  ✅ {len(game_contexts)}개 컨텍스트 로드")
        return game_contexts

    # ========================================================================
    # Step 3: 게임 파싱
    # ========================================================================

    def parse_game(self, game_data: Dict, context: Dict) -> Optional[Dict]:
        """게임 데이터 파싱"""
        try:
            header = game_data['header']
            competition = header['competitions'][0]
            competitors = competition['competitors']

            # 홈/어웨이 팀
            home_team = None
            away_team = None
            for comp in competitors:
                team_abbr = comp['team']['abbreviation']
                if comp['homeAway'] == 'home':
                    home_team = {
                        'abbr': team_abbr,
                        'name': comp['team']['displayName'],
                        'score': int(comp['score'])
                    }
                else:
                    away_team = {
                        'abbr': team_abbr,
                        'name': comp['team']['displayName'],
                        'score': int(comp['score'])
                    }

            if not home_team or not away_team:
                return None

            # 경기 결과
            parsed = {
                'game_id': header['id'],
                'date': competition['date'][:10],
                'season': header['season']['year'],

                'home_team': home_team,
                'away_team': away_team,

                'home_win': home_team['score'] > away_team['score'],

                # 컨텍스트
                'home_rest_days': context.get('home_rest_days', 0),
                'away_rest_days': context.get('away_rest_days', 0),

                # Venue
                'venue': self.parse_venue(game_data),

                # Officials
                'officials': self.parse_officials(game_data),

                # Team stats
                'team_stats': self.parse_team_stats(game_data),

                # Players
                'players': self.parse_players(game_data)
            }

            return parsed

        except Exception as e:
            print(f"    ⚠️  파싱 실패: {e}")
            return None

    def parse_venue(self, game_data: Dict) -> Optional[Dict]:
        """경기장 정보"""
        try:
            venue_data = game_data['gameInfo']['venue']
            return {
                'id': venue_data['id'],
                'name': venue_data['fullName'],
                'city': venue_data.get('address', {}).get('city', 'Unknown')
            }
        except:
            return None

    def parse_officials(self, game_data: Dict) -> List[Dict]:
        """심판 정보"""
        try:
            officials = game_data['gameInfo']['officials']
            return [
                {
                    'name': official['displayName'],
                    'position': official.get('position', {}).get('name', 'Referee'),
                    'order': official.get('order', 0)
                }
                for official in officials
            ]
        except:
            return []

    def parse_team_stats(self, game_data: Dict) -> Dict:
        """팀 통계"""
        try:
            teams = game_data['boxscore']['teams']
            stats = {}

            for team_data in teams:
                team_abbr = team_data['team']['abbreviation']
                team_stats_array = team_data['statistics']

                # 통계 배열을 딕셔너리로
                stats_dict = {}
                for stat in team_stats_array:
                    name = stat['name']
                    value_str = stat.get('displayValue', '0')
                    if '-' in value_str:
                        value_str = value_str.split('-')[0]
                    try:
                        stats_dict[name] = float(value_str) if '.' in value_str else int(value_str)
                    except:
                        stats_dict[name] = 0

                stats[team_abbr] = stats_dict

            return stats
        except:
            return {}

    def parse_players(self, game_data: Dict) -> List[Dict]:
        """선수 출전 기록"""
        try:
            players_data = game_data['boxscore']['players']
            all_players = []

            for team_data in players_data:
                team_abbr = team_data['team']['abbreviation']
                team_side = 'home' if team_data['homeAway'] == 'home' else 'away'

                # athletes 배열
                if 'statistics' not in team_data or not team_data['statistics']:
                    continue

                for stat_group in team_data['statistics']:
                    if 'athletes' not in stat_group:
                        continue

                    for athlete in stat_group['athletes']:
                        try:
                            player_name = athlete['athlete']['displayName']
                            stats = athlete['stats']  # 통계 배열

                            # 통계 파싱
                            minutes_str = stats[0] if len(stats) > 0 else '0'  # MIN
                            minutes = self.parse_minutes(minutes_str)

                            if minutes == 0:
                                continue  # DNP

                            player_record = {
                                'name': player_name,
                                'team': team_side,
                                'team_abbr': team_abbr,
                                'starter': athlete.get('starter', False),
                                'minutes': minutes,
                                'points': int(stats[12]) if len(stats) > 12 else 0,  # PTS
                                'rebounds': int(stats[7]) if len(stats) > 7 else 0,  # REB
                                'assists': int(stats[8]) if len(stats) > 8 else 0,  # AST
                                'fg_pct': self.parse_pct(stats[2]) if len(stats) > 2 else 0.0,  # FG%
                                'plus_minus': self.parse_plus_minus(stats[13]) if len(stats) > 13 else 0  # +/-
                            }

                            all_players.append(player_record)
                        except Exception as e:
                            pass  # 선수 파싱 실패는 조용히 스킵

            return all_players
        except:
            return []

    def parse_minutes(self, minutes_str: str) -> int:
        """분:초 → 분"""
        try:
            if ':' in minutes_str:
                parts = minutes_str.split(':')
                return int(parts[0])
            return int(minutes_str)
        except:
            return 0

    def parse_pct(self, pct_str: str) -> float:
        """퍼센트 파싱"""
        try:
            return float(pct_str) / 100.0 if float(pct_str) > 1 else float(pct_str)
        except:
            return 0.0

    def parse_plus_minus(self, pm_str: str) -> int:
        """+/- 파싱"""
        try:
            return int(pm_str)
        except:
            return 0

    # ========================================================================
    # Step 4: Neo4j 임포트
    # ========================================================================

    def import_games(self, games: List[Dict], contexts: Dict):
        """게임 데이터를 Neo4j로 임포트"""
        print("\n" + "=" * 70)
        print("Step 3: Neo4j 임포트")
        print("=" * 70)

        with self.driver.session() as session:
            for i, game in enumerate(games, 1):
                game_id = game['game_id']
                game_data = game['data']
                context = contexts.get(game_id, {})

                parsed = self.parse_game(game_data, context)
                if not parsed:
                    print(f"  [{i}/{len(games)}] ⚠️  {game_id}: 파싱 실패")
                    continue

                try:
                    # 게임 노드 생성
                    self.create_game_node(session, parsed)

                    # 관계 생성
                    if parsed['venue']:
                        self.create_venue(session, parsed['venue'])
                        self.link_venue(session, parsed['game_id'], parsed['venue']['id'])

                    for official in parsed['officials']:
                        self.create_official(session, official)
                        self.link_official(session, parsed['game_id'], official)

                    for player in parsed['players']:
                        self.create_player(session, player)
                        self.link_player(session, parsed['game_id'], player)

                    self.stats['games'] += 1
                    if i % 50 == 0:
                        print(f"  [{i}/{len(games)}] ✅ 진행 중...")

                except Exception as e:
                    print(f"  [{i}/{len(games)}] ⚠️  {game_id}: {str(e)[:50]}")

        print(f"\n  ✅ {self.stats['games']}개 게임 임포트 완료")

    def create_game_node(self, session, parsed: Dict):
        """GameState 노드 생성"""
        # 팀 노드 먼저 생성
        for team in [parsed['home_team'], parsed['away_team']]:
            session.run("""
                MERGE (t:Team {abbr: $abbr})
                SET t.name = $name
            """, abbr=team['abbr'], name=team['name'])

        # 게임 노드
        session.run("""
            CREATE (g:GameState {
                game_id: $game_id,
                date: date($date),
                season: $season,

                home_team: $home_team,
                away_team: $away_team,
                home_score: $home_score,
                away_score: $away_score,
                home_win: $home_win,

                home_rest_days: $home_rest_days,
                away_rest_days: $away_rest_days
            })
        """,
            game_id=parsed['game_id'],
            date=parsed['date'],
            season=str(parsed['season']),
            home_team=parsed['home_team']['abbr'],
            away_team=parsed['away_team']['abbr'],
            home_score=parsed['home_team']['score'],
            away_score=parsed['away_team']['score'],
            home_win=parsed['home_win'],
            home_rest_days=parsed['home_rest_days'],
            away_rest_days=parsed['away_rest_days']
        )

    def create_venue(self, session, venue: Dict):
        """Venue 노드"""
        session.run("""
            MERGE (v:Venue {id: $id})
            SET v.name = $name, v.city = $city
        """, **venue)
        self.stats['venues'] += 1

    def link_venue(self, session, game_id: str, venue_id: str):
        """게임 → 경기장"""
        session.run("""
            MATCH (g:GameState {game_id: $game_id})
            MATCH (v:Venue {id: $venue_id})
            CREATE (g)-[:HOSTED_AT]->(v)
        """, game_id=game_id, venue_id=venue_id)

    def create_official(self, session, official: Dict):
        """Referee 노드"""
        session.run("""
            MERGE (r:Referee {name: $name})
        """, name=official['name'])
        self.stats['referees'] += 1

    def link_official(self, session, game_id: str, official: Dict):
        """게임 → 심판"""
        session.run("""
            MATCH (g:GameState {game_id: $game_id})
            MATCH (r:Referee {name: $name})
            CREATE (g)-[:OFFICIATED_BY {position: $position, order: $order}]->(r)
        """, game_id=game_id, **official)

    def create_player(self, session, player: Dict):
        """Player 노드"""
        session.run("""
            MERGE (p:Player {name: $name})
        """, name=player['name'])
        self.stats['players'] += 1

    def link_player(self, session, game_id: str, player: Dict):
        """게임 → 선수"""
        session.run("""
            MATCH (g:GameState {game_id: $game_id})
            MATCH (p:Player {name: $name})
            CREATE (g)-[:PLAYED {
                team: $team,
                team_abbr: $team_abbr,
                starter: $starter,
                minutes: $minutes,
                points: $points,
                rebounds: $rebounds,
                assists: $assists,
                fg_pct: $fg_pct,
                plus_minus: $plus_minus
            }]->(p)
        """, game_id=game_id, **player)

    # ========================================================================
    # 실행
    # ========================================================================

    def run(self, limit: Optional[int] = None):
        """전체 마이그레이션 실행"""
        print("=" * 70)
        print(f"깨끗한 Neo4j 마이그레이션 시작 {f'(최대 {limit}개)' if limit else ''}")
        print("=" * 70)

        self.create_constraints()
        games = self.load_games(limit)
        contexts = self.load_snapshots()
        self.import_games(games, contexts)

        print("\n" + "=" * 70)
        print("✅ 마이그레이션 완료!")
        print("=" * 70)
        print(f"\n통계:")
        print(f"  게임: {self.stats['games']}개")
        print(f"  선수: {self.stats['players']}명 (중복 포함)")
        print(f"  심판: {self.stats['referees']}명 (중복 포함)")
        print(f"  경기장: {self.stats['venues']}개 (중복 포함)")


# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="password123")
    parser.add_argument("--limit", type=int, help="게임 수 제한 (테스트용)")
    args = parser.parse_args()

    migration = CleanMigration(args.uri, args.user, args.password)
    try:
        migration.run(args.limit)
    finally:
        migration.close()

    print("\n다음 단계:")
    print("1. Neo4j Browser: http://localhost:7474")
    print("2. 쿼리: MATCH (n) RETURN n LIMIT 50")
