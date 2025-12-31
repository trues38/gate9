#!/usr/bin/env python3
"""
NBA 데이터 검증 파이프라인
크론 → 데이터 수집 → 검증 → 파이프라인 → 보고서
"""
from neo4j import GraphDatabase
import json
from datetime import datetime
from typing import Dict, List

class NBADataValidator:
    """NBA 데이터 완전성 검증기"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.validation_report = {
            "timestamp": datetime.now().isoformat(),
            "teams": {},
            "issues": [],
            "warnings": [],
            "summary": {}
        }

    def validate_team(self, team_abbr: str) -> Dict:
        """팀 데이터 검증"""
        team_data = {"team": team_abbr}

        with self.driver.session() as session:
            # 1. Team 노드 확인 (올바른 속성: team_abbr)
            team_check = session.run("""
                MATCH (t:Team {team_abbr: $team})
                RETURN t.name as name, t.team_abbr as abbr
            """, team=team_abbr).data()

            if not team_check:
                self.validation_report["issues"].append(f"{team_abbr}: Team 노드 없음")
                team_data["team_node"] = False
                return team_data

            team_data["team_node"] = True
            team_data["team_name"] = team_check[0]['name']

            # 2. 선수 로스터 확인
            roster_check = session.run("""
                MATCH (p:Player)-[:PLAYS_FOR]->(t:Team {team_abbr: $team})
                RETURN count(p) as player_count,
                       collect(p.name)[..5] as sample_players
            """, team=team_abbr).data()

            if roster_check:
                player_count = roster_check[0]['player_count']
                team_data["roster_count"] = player_count
                team_data["sample_players"] = roster_check[0]['sample_players']

                if player_count == 0:
                    self.validation_report["warnings"].append(f"{team_abbr}: 선수 로스터 없음")
                elif player_count < 10:
                    self.validation_report["warnings"].append(f"{team_abbr}: 선수 부족 ({player_count}명)")

            # 3. 최근 경기 데이터 확인
            recent_games = session.run("""
                MATCH (g:Game)
                WHERE g.home_team = $team OR g.away_team = $team
                RETURN g.date as date, g.game_id as game_id, g.status as status
                ORDER BY g.date DESC
                LIMIT 5
            """, team=team_abbr).data()

            team_data["recent_games_count"] = len(recent_games)
            team_data["recent_games"] = recent_games

            if len(recent_games) < 5:
                self.validation_report["warnings"].append(
                    f"{team_abbr}: 최근 경기 부족 ({len(recent_games)}/5개)"
                )

            # 4. PlayerStats 데이터 확인 (최근 1경기)
            if recent_games:
                latest_game_id = recent_games[0]['game_id']

                # Game -> PlayerStats 관계 확인
                stats_check = session.run("""
                    MATCH (g:Game {game_id: $game_id})<-[:IN_GAME]-(ps:PlayerStats)
                    RETURN count(ps) as stats_count
                """, game_id=latest_game_id).data()

                if stats_check:
                    stats_count = stats_check[0]['stats_count']
                    team_data["latest_game_stats"] = stats_count

                    if stats_count == 0:
                        self.validation_report["warnings"].append(
                            f"{team_abbr}: 최근 경기 PlayerStats 없음 (Game: {latest_game_id})"
                        )
                    elif stats_count < 10:
                        self.validation_report["warnings"].append(
                            f"{team_abbr}: PlayerStats 부족 ({stats_count}개)"
                        )

        return team_data

    def validate_games(self, games: List[Dict]) -> Dict:
        """경기 데이터 검증"""
        games_validation = {}

        for idx, game in enumerate(games, 1):
            game_key = f"game{idx}"
            away_data = self.validate_team(game['away'])
            home_data = self.validate_team(game['home'])

            games_validation[game_key] = {
                "matchup": f"{game['away_full']} @ {game['home_full']}",
                "away": away_data,
                "home": home_data
            }

            self.validation_report["teams"][game['away']] = away_data
            self.validation_report["teams"][game['home']] = home_data

        return games_validation

    def generate_summary(self):
        """검증 결과 요약"""
        total_teams = len(self.validation_report["teams"])
        teams_with_roster = sum(
            1 for t in self.validation_report["teams"].values()
            if t.get("roster_count", 0) > 0
        )
        teams_with_games = sum(
            1 for t in self.validation_report["teams"].values()
            if t.get("recent_games_count", 0) >= 5
        )
        teams_with_stats = sum(
            1 for t in self.validation_report["teams"].values()
            if t.get("latest_game_stats", 0) > 0
        )

        self.validation_report["summary"] = {
            "total_teams": total_teams,
            "teams_with_roster": teams_with_roster,
            "teams_with_games": teams_with_games,
            "teams_with_stats": teams_with_stats,
            "total_issues": len(self.validation_report["issues"]),
            "total_warnings": len(self.validation_report["warnings"]),
            "validation_passed": len(self.validation_report["issues"]) == 0
        }

    def print_report(self):
        """검증 리포트 출력"""
        print("=" * 80)
        print("🔍 NBA 데이터 검증 파이프라인")
        print("=" * 80)

        for team_abbr, team_data in self.validation_report["teams"].items():
            print(f"\n📊 {team_abbr} ({team_data.get('team_name', 'Unknown')})")
            print("-" * 80)

            if team_data.get("team_node"):
                print(f"  ✅ Team 노드: OK")
            else:
                print(f"  ❌ Team 노드: 없음")

            roster_count = team_data.get("roster_count", 0)
            if roster_count > 0:
                print(f"  ✅ 선수 로스터: {roster_count}명")
                if team_data.get("sample_players"):
                    print(f"     샘플: {', '.join(team_data['sample_players'][:3])}")
            else:
                print(f"  ⚠️ 선수 로스터: 없음")

            games_count = team_data.get("recent_games_count", 0)
            if games_count >= 5:
                print(f"  ✅ 최근 경기: {games_count}개")
            else:
                print(f"  ⚠️ 최근 경기: {games_count}/5개")

            stats_count = team_data.get("latest_game_stats", 0)
            if stats_count > 0:
                print(f"  ✅ 최근 경기 PlayerStats: {stats_count}개")
            else:
                print(f"  ⚠️ 최근 경기 PlayerStats: 없음")

        print("\n" + "=" * 80)
        print("📋 검증 요약")
        print("=" * 80)

        summary = self.validation_report["summary"]
        print(f"총 팀: {summary['total_teams']}개")
        print(f"로스터 있는 팀: {summary['teams_with_roster']}/{summary['total_teams']}개")
        print(f"최근 5경기 있는 팀: {summary['teams_with_games']}/{summary['total_teams']}개")
        print(f"PlayerStats 있는 팀: {summary['teams_with_stats']}/{summary['total_teams']}개")
        print(f"Critical Issues: {summary['total_issues']}개")
        print(f"Warnings: {summary['total_warnings']}개")

        if self.validation_report["issues"]:
            print("\n❌ Critical Issues:")
            for issue in self.validation_report["issues"]:
                print(f"  - {issue}")

        if self.validation_report["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in self.validation_report["warnings"]:
                print(f"  - {warning}")

        if self.validation_report["summary"]["validation_passed"]:
            print("\n✅ 모든 검증 통과!")
        else:
            print("\n⚠️ 일부 검증 실패 - 보고서 생성 가능하나 품질 제한적")

    def save_report(self, output_file: str):
        """검증 리포트 저장"""
        with open(output_file, 'w') as f:
            json.dump(self.validation_report, f, indent=2, default=str)
        print(f"\n📄 검증 리포트 저장: {output_file}")

    def close(self):
        """연결 종료"""
        self.driver.close()


if __name__ == "__main__":
    # Tomorrow's 4 games
    games = [
        {"away": "GS", "home": "CHA", "away_full": "Golden State Warriors", "home_full": "Charlotte Hornets"},
        {"away": "MIN", "home": "ATL", "away_full": "Minnesota Timberwolves", "home_full": "Atlanta Hawks"},
        {"away": "ORL", "home": "IND", "away_full": "Orlando Magic", "home_full": "Indiana Pacers"},
        {"away": "PHX", "home": "CLE", "away_full": "Phoenix Suns", "home_full": "Cleveland Cavaliers"}
    ]

    # Initialize validator
    validator = NBADataValidator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="nba_vultr_2025"
    )

    # Run validation
    validator.validate_games(games)
    validator.generate_summary()
    validator.print_report()
    validator.save_report('/tmp/nba_validation_report.json')
    validator.close()

    # Return exit code
    import sys
    sys.exit(0 if validator.validation_report["summary"]["validation_passed"] else 1)
