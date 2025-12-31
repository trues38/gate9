#!/usr/bin/env python3
"""
Lineup 노드 임포터 (v2.0)

JSON 파일에서 라인업 정의를 읽어 Neo4j에 임포트:
- Lineup 노드 생성
- Player와 관계 연결
- Coach와 관계 연결

사용법:
  python import_lineups.py lineups.json
  python import_lineups.py lineups_example.json  # 테스트
"""

import json
from neo4j import GraphDatabase
from typing import Dict, List
import sys

class LineupImporter:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def validate_lineup(self, team: str, lineup: Dict) -> bool:
        """라인업 유효성 검사"""

        required_fields = ['name', 'players', 'usage_pct', 'style', 'tempo_boost', 'defense_rating', 'offense_rating']

        for field in required_fields:
            if field not in lineup:
                print(f"  ⚠️  필수 필드 누락: {field}")
                return False

        if len(lineup['players']) != 5:
            print(f"  ⚠️  선수는 정확히 5명이어야 함 (현재 {len(lineup['players'])}명)")
            return False

        if not 0 <= lineup['usage_pct'] <= 100:
            print(f"  ⚠️  usage_pct는 0-100 사이 값 (현재 {lineup['usage_pct']})")
            return False

        return True

    def create_lineup_node(self, team: str, lineup: Dict):
        """Lineup 노드 생성 및 관계 연결"""

        lineup_id = f"{team}_{lineup['name'].replace(' ', '_').lower()}"

        query = """
        MERGE (lineup:Lineup {lineup_id: $lineup_id})
        SET lineup.team = $team,
            lineup.name = $name,
            lineup.players = $players,
            lineup.player_count = $player_count,
            lineup.usage_pct = $usage_pct,
            lineup.style = $style,
            lineup.tempo_boost = $tempo_boost,
            lineup.defense_rating = $defense_rating,
            lineup.offense_rating = $offense_rating,
            lineup.notes = $notes,
            lineup.season = $season,
            lineup.updated_at = datetime()

        WITH lineup

        // Coach 연결
        MATCH (coach:Coach {team: $team, season: $season})
        MERGE (coach)-[:USES_LINEUP]->(lineup)

        WITH lineup

        // Player 연결
        UNWIND $players AS player_name
        MATCH (p:Player {name: player_name, team: $team})
        MERGE (lineup)-[:INCLUDES]->(p)
        """

        with self.driver.session() as session:
            session.run(query,
                lineup_id=lineup_id,
                team=team,
                name=lineup['name'],
                players=lineup['players'],
                player_count=len(lineup['players']),
                usage_pct=lineup['usage_pct'],
                style=lineup['style'],
                tempo_boost=lineup['tempo_boost'],
                defense_rating=lineup['defense_rating'],
                offense_rating=lineup['offense_rating'],
                notes=lineup.get('notes', ''),
                season="2025-26"
            )

    def verify_players(self, team: str, players: List[str]) -> List[str]:
        """선수 존재 여부 확인"""

        query = """
        MATCH (p:Player)
        WHERE p.name IN $players AND p.team = $team
        RETURN p.name AS name
        """

        with self.driver.session() as session:
            result = session.run(query, players=players, team=team)
            found = {record['name'] for record in result}
            missing = set(players) - found
            return list(missing)

    def import_from_file(self, filepath: str):
        """JSON 파일에서 라인업 임포트"""

        print("=" * 80)
        print("Lineup 노드 임포터 (v2.0)")
        print("=" * 80)
        print(f"파일: {filepath}")
        print()

        # JSON 읽기
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ 파일 없음: {filepath}")
            return
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            return

        # 팀별 처리
        total_lineups = 0
        total_teams = 0

        for team, team_data in sorted(data.items()):
            lineups = team_data.get('lineups', [])

            if not lineups:
                continue

            print(f"처리 중: {team} ({len(lineups)}개 라인업)")
            total_teams += 1

            for lineup in lineups:
                # 유효성 검사
                if not self.validate_lineup(team, lineup):
                    print(f"  ✗ {lineup.get('name', '?')} - 유효성 검사 실패")
                    continue

                # 선수 존재 확인
                missing = self.verify_players(team, lineup['players'])
                if missing:
                    print(f"  ⚠️  {lineup['name']} - 선수 미존재: {', '.join(missing)}")
                    print(f"     → Player 노드를 먼저 생성하세요 (expand_player_attributes.py)")
                    continue

                # 임포트
                try:
                    self.create_lineup_node(team, lineup)
                    print(f"  ✅ {lineup['name']:20s} - {', '.join(lineup['players'][:3])}... ({lineup['usage_pct']}%)")
                    total_lineups += 1
                except Exception as e:
                    print(f"  ✗ {lineup['name']} - 오류: {e}")

            print()

        print("=" * 80)
        print(f"✅ {total_teams}개 팀, {total_lineups}개 라인업 임포트 완료")
        print("=" * 80)
        print()

        # 요약
        self.print_summary()

    def print_summary(self):
        """임포트 요약 출력"""

        query = """
        MATCH (lineup:Lineup)
        RETURN lineup.team AS team,
               count(*) AS lineup_count,
               sum(lineup.usage_pct) AS total_usage
        ORDER BY team
        """

        with self.driver.session() as session:
            result = session.run(query)
            records = list(result)

            if not records:
                print("⚠️  임포트된 라인업 없음")
                return

            print("📊 팀별 라인업 요약:")
            for record in records:
                team = record['team']
                count = record['lineup_count']
                usage = record['total_usage']
                print(f"  {team}: {count}개 라인업 (총 사용률 {usage}%)")

def main():
    if len(sys.argv) < 2:
        print("사용법: python import_lineups.py <json_file>")
        print()
        print("예시:")
        print("  python import_lineups.py lineups.json")
        print("  python import_lineups.py lineups_example.json")
        sys.exit(1)

    filepath = sys.argv[1]
    importer = LineupImporter()

    try:
        importer.import_from_file(filepath)
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()

if __name__ == "__main__":
    main()
