#!/usr/bin/env python3
"""
Lineup 무결성 검증

- 모든 라인업의 선수가 DB에 존재하는지 확인
- 최근 트레이드/부상으로 인한 문제 감지
- 누락된 팀 라인업 리포트
"""

from neo4j import GraphDatabase
from typing import Dict, List, Set
from collections import defaultdict

class LineupVerifier:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_all_lineups(self) -> List[Dict]:
        """모든 라인업 가져오기"""
        query = """
        MATCH (lineup:Lineup)
        RETURN lineup.team AS team,
               lineup.name AS name,
               lineup.players AS players,
               lineup.lineup_id AS lineup_id
        ORDER BY lineup.team, lineup.usage_pct DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def get_player_teams(self) -> Dict[str, str]:
        """선수별 현재 팀"""
        query = """
        MATCH (p:Player)
        WHERE p.team IS NOT NULL
        RETURN p.name AS name, p.team AS team
        """

        with self.driver.session() as session:
            result = session.run(query)
            return {record['name']: record['team'] for record in result}

    def get_teams_with_lineups(self) -> Set[str]:
        """라인업이 있는 팀"""
        query = """
        MATCH (lineup:Lineup)
        RETURN DISTINCT lineup.team AS team
        """

        with self.driver.session() as session:
            result = session.run(query)
            return {record['team'] for record in result}

    def verify(self):
        """라인업 검증 실행"""
        print("=" * 80)
        print("Lineup 무결성 검증")
        print("=" * 80)
        print()

        # 데이터 수집
        lineups = self.get_all_lineups()
        player_teams = self.get_player_teams()
        teams_with_lineups = self.get_teams_with_lineups()

        if not lineups:
            print("⚠️  라인업 데이터 없음")
            print()
            print("다음 단계:")
            print("  1. lineups.json 작성")
            print("  2. python import_lineups.py lineups.json 실행")
            return

        print(f"검증 중: {len(lineups)}개 라인업 ({len(teams_with_lineups)}개 팀)")
        print()

        # 문제 추적
        issues = defaultdict(list)
        valid_count = 0

        # 각 라인업 검증
        for lineup in lineups:
            team = lineup['team']
            name = lineup['name']
            players = lineup['players']

            lineup_issues = []

            for player_name in players:
                # 선수가 DB에 있는지
                if player_name not in player_teams:
                    lineup_issues.append(f"'{player_name}' - DB에 없음")
                    continue

                # 선수가 올바른 팀에 있는지
                current_team = player_teams[player_name]
                if current_team != team:
                    lineup_issues.append(f"'{player_name}' - 현재 {current_team} (트레이드?)")

            if lineup_issues:
                issues[team].append({
                    'lineup': name,
                    'problems': lineup_issues
                })
            else:
                valid_count += 1

        # 결과 출력
        print("-" * 80)
        print(f"검증 결과")
        print("-" * 80)
        print()

        if issues:
            print(f"⚠️  문제 발견: {len(issues)}개 팀, {len(lineups) - valid_count}개 라인업")
            print()

            for team, team_issues in sorted(issues.items()):
                print(f"🔴 {team}")
                for issue in team_issues:
                    print(f"   라인업: {issue['lineup']}")
                    for problem in issue['problems']:
                        print(f"     - {problem}")
                print()

            print("해결 방법:")
            print("  1. lineups.json 수정 (선수 이름 업데이트)")
            print("  2. python import_lineups.py lineups.json 재실행")
            print()

        else:
            print(f"✅ 모든 라인업 검증 완료 ({valid_count}/{len(lineups)})")
            print()

        # 라인업 없는 팀
        all_teams = {
            "ATL", "BKN", "BOS", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
            "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
            "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"
        }
        missing_teams = all_teams - teams_with_lineups

        if missing_teams:
            print("-" * 80)
            print(f"라인업 미입력 팀: {len(missing_teams)}개")
            print("-" * 80)
            print()

            # 우선순위별 분류
            priority_teams = {"HOU", "OKC", "BOS", "LAL", "DEN", "NYK", "MIL", "PHI", "CLE", "GSW"}
            priority_missing = missing_teams & priority_teams
            others_missing = missing_teams - priority_teams

            if priority_missing:
                print(f"🔴 우선순위 팀 ({len(priority_missing)}개):")
                for team in sorted(priority_missing):
                    print(f"   - {team}")
                print()

            if others_missing:
                print(f"⚪ 기타 팀 ({len(others_missing)}개):")
                for team in sorted(others_missing):
                    print(f"   - {team}")
                print()

        print("=" * 80)

def main():
    verifier = LineupVerifier()

    try:
        verifier.verify()
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        verifier.close()

if __name__ == "__main__":
    main()
