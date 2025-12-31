#!/usr/bin/env python3
"""
Coach 노드 자동 생성 (v2.0)

PlayerBoxScore 데이터에서 코치 성향 계산:
- 로테이션 깊이 (rotation_depth)
- 주전 평균 출전 시간 (avg_starter_minutes)
- 벤치 평균 출전 시간 (avg_bench_minutes)
- 템포 (tempo)
- 경기 수, 승률

25-26 시즌 데이터 기반
"""

import requests
from neo4j import GraphDatabase
from typing import Dict, List, Optional
from collections import defaultdict
import json

class CoachStatsCalculator:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # 현재 시즌 코치 정보 (수동 입력)
        # TODO: 자동 수집 가능하면 ESPN API에서 가져오기
        self.current_coaches = {
            "ATL": "Quin Snyder",
            "BOS": "Joe Mazzulla",
            "BKN": "Jordi Fernández",
            "CHA": "Charles Lee",
            "CHI": "Billy Donovan",
            "CLE": "Kenny Atkinson",
            "DAL": "Jason Kidd",
            "DEN": "Michael Malone",
            "DET": "J.B. Bickerstaff",
            "GSW": "Steve Kerr",
            "HOU": "Ime Udoka",
            "IND": "Rick Carlisle",
            "LAC": "Tyronn Lue",
            "LAL": "JJ Redick",
            "MEM": "Taylor Jenkins",
            "MIA": "Erik Spoelstra",
            "MIL": "Doc Rivers",
            "MIN": "Chris Finch",
            "NOP": "Willie Green",
            "NYK": "Tom Thibodeau",
            "OKC": "Mark Daigneault",
            "ORL": "Jamahl Mosley",
            "PHI": "Nick Nurse",
            "PHX": "Mike Budenholzer",
            "POR": "Chauncey Billups",
            "SAC": "Doug Christie",
            "SAS": "Mitch Johnson",
            "TOR": "Darko Rajaković",
            "UTA": "Will Hardy",
            "WAS": "Brian Keefe"
        }

    def close(self):
        self.driver.close()

    def calculate_rotation_stats(self, team: str, season_start='2025-10-01') -> Dict:
        """
        팀의 로테이션 패턴 계산
        - rotation_depth: 평균 20분+ 선수 수
        - avg_starter_minutes: 30분+ 선수 평균
        - avg_bench_minutes: 20분 미만 선수 평균
        """

        query = """
        MATCH (g:GameState)-[:HAS_BOXSCORE]->(pb:PlayerBoxScore)
        WHERE pb.team = $team
          AND g.date >= date($season_start)
          AND pb.minutes IS NOT NULL
        WITH g.game_id AS game,
             collect({name: pb.player_name, min: pb.minutes}) AS players
        WITH game,
             [p IN players WHERE p.min >= 20] AS rotation_players,
             [p IN players WHERE p.min >= 30] AS starters,
             [p IN players WHERE p.min < 20 AND p.min > 0] AS bench_players
        RETURN
          avg(size(rotation_players)) AS avg_rotation_depth,
          avg([p IN starters | p.min][0]) AS avg_starter_minutes,
          avg([p IN bench_players | p.min][0]) AS avg_bench_minutes,
          count(DISTINCT game) AS games
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, season_start=season_start).single()

            if not result or result['games'] == 0:
                return None

            return {
                'rotation_depth': round(result['avg_rotation_depth'], 1) if result['avg_rotation_depth'] else 0,
                'avg_starter_minutes': round(result['avg_starter_minutes'], 1) if result['avg_starter_minutes'] else 0,
                'avg_bench_minutes': round(result['avg_bench_minutes'], 1) if result['avg_bench_minutes'] else 0,
                'games': result['games']
            }

    def calculate_team_record(self, team: str, season_start='2025-10-01') -> Dict:
        """팀 전적 계산"""

        query = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date($season_start)
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_win ELSE NOT g.home_win END AS win
        RETURN
          count(*) AS games,
          sum(CASE WHEN win THEN 1 ELSE 0 END) AS wins
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, season_start=season_start).single()

            if not result or result['games'] == 0:
                return None

            return {
                'games_coached': result['games'],
                'wins': result['wins'],
                'win_pct': round(result['wins'] / result['games'], 3)
            }

    def estimate_tempo(self, team: str, season_start='2025-10-01') -> Optional[float]:
        """
        템포 추정 (possessions per game)

        정확한 템포 계산:
        Possessions ≈ FGA + 0.44*FTA + TO - ORB

        현재는 간단히 득점 기반 추정:
        Tempo ≈ (Team Score + Opp Score) / 2 * 1.1

        TODO: ESPN API에서 실제 Pace 통계 가져오기
        """

        query = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date($season_start)
        WITH g,
             CASE WHEN g.home_team = $team THEN g.home_score ELSE g.away_score END AS team_score,
             CASE WHEN g.home_team = $team THEN g.away_score ELSE g.home_score END AS opp_score
        RETURN avg(team_score + opp_score) AS avg_total_score
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, season_start=season_start).single()

            if not result or result['avg_total_score'] is None:
                return None

            # 간단한 템포 추정 (실제 Pace는 100 전후)
            # Total score 220점 → 템포 약 100
            tempo = result['avg_total_score'] / 2.2
            return round(tempo, 1)

    def calculate_rookie_veteran_bias(self, team: str, season_start='2025-10-01') -> Dict:
        """
        루키/베테랑 선호도 계산

        간단한 방식: 평균 출전 시간 기준
        - rookie_trust: 신인(1-2년차) 평균 출전 / 주전 출전
        - veteran_bias: 베테랑(5년차+) 평균 출전 / 주전 출전

        TODO: 선수 경력 정보 필요 (ESPN에서 수집 가능)
        현재는 placeholder로 0.5 반환
        """

        # 향후 구현 예정
        return {
            'rookie_trust': 0.5,
            'veteran_bias': 0.5
        }

    def create_coach_node(self, team: str, coach_name: str, stats: Dict):
        """Coach 노드 생성/업데이트"""

        query = """
        MERGE (coach:Coach {team: $team, season: $season})
        SET coach.name = $name,
            coach.rotation_depth = $rotation_depth,
            coach.avg_starter_minutes = $avg_starter_minutes,
            coach.avg_bench_minutes = $avg_bench_minutes,
            coach.tempo = $tempo,
            coach.games_coached = $games_coached,
            coach.win_pct = $win_pct,
            coach.rookie_trust = $rookie_trust,
            coach.veteran_bias = $veteran_bias,
            coach.updated_at = datetime()
        RETURN coach
        """

        with self.driver.session() as session:
            session.run(query,
                team=team,
                season="2025-26",
                name=coach_name,
                rotation_depth=stats.get('rotation_depth', 0),
                avg_starter_minutes=stats.get('avg_starter_minutes', 0),
                avg_bench_minutes=stats.get('avg_bench_minutes', 0),
                tempo=stats.get('tempo', 0),
                games_coached=stats.get('games_coached', 0),
                win_pct=stats.get('win_pct', 0),
                rookie_trust=stats.get('rookie_trust', 0.5),
                veteran_bias=stats.get('veteran_bias', 0.5)
            )

    def process_all_teams(self, season_start='2025-10-01'):
        """모든 팀의 Coach 노드 생성"""

        print("=" * 80)
        print("Coach 노드 자동 생성 (v2.0)")
        print("=" * 80)
        print(f"시즌: 2025-26 (from {season_start})")
        print(f"팀: {len(self.current_coaches)}개")
        print()

        results = []

        for team, coach_name in sorted(self.current_coaches.items()):
            print(f"처리 중: {team} - {coach_name}")

            # 로테이션 통계
            rotation_stats = self.calculate_rotation_stats(team, season_start)
            if not rotation_stats:
                print(f"  ⚠️  데이터 없음 (PlayerBoxScore 없음)")
                continue

            # 전적
            record = self.calculate_team_record(team, season_start)
            if not record:
                print(f"  ⚠️  전적 데이터 없음")
                continue

            # 템포
            tempo = self.estimate_tempo(team, season_start)

            # 루키/베테랑 (현재 placeholder)
            bias = self.calculate_rookie_veteran_bias(team, season_start)

            # 통합
            stats = {
                **rotation_stats,
                **record,
                'tempo': tempo,
                **bias
            }

            # Neo4j 저장
            self.create_coach_node(team, coach_name, stats)

            # 출력
            print(f"  ✅ 로테이션: {stats['rotation_depth']}명 "
                  f"(주전 {stats['avg_starter_minutes']}분, 벤치 {stats['avg_bench_minutes']}분)")
            print(f"     템포: {stats['tempo']}, "
                  f"전적: {record['wins']}-{record['games_coached']-record['wins']} ({stats['win_pct']:.1%})")
            print()

            results.append({
                'team': team,
                'coach': coach_name,
                'stats': stats
            })

        print("=" * 80)
        print(f"✅ {len(results)}개 팀 Coach 노드 생성 완료")
        print("=" * 80)
        print()

        # 요약 통계
        if results:
            print("📊 코치별 로테이ション 깊이 순위:")
            sorted_by_rotation = sorted(results, key=lambda x: x['stats']['rotation_depth'], reverse=True)
            for i, r in enumerate(sorted_by_rotation[:10], 1):
                print(f"  {i:2d}. {r['team']} {r['coach']:20s} - {r['stats']['rotation_depth']}명")

            print()
            print("📊 코치별 주전 혹사 순위 (낮을수록 혹사):")
            sorted_by_starter = sorted(results, key=lambda x: x['stats']['rotation_depth'] / x['stats']['avg_starter_minutes'] if x['stats']['avg_starter_minutes'] > 0 else 0)
            for i, r in enumerate(sorted_by_starter[:10], 1):
                ratio = r['stats']['rotation_depth'] / r['stats']['avg_starter_minutes'] if r['stats']['avg_starter_minutes'] > 0 else 0
                print(f"  {i:2d}. {r['team']} {r['coach']:20s} - 주전 {r['stats']['avg_starter_minutes']}분 (비율 {ratio:.3f})")

        return results

def main():
    calculator = CoachStatsCalculator()

    try:
        results = calculator.process_all_teams()

        # 결과 저장 (선택)
        with open('coach_stats_2025_26.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print()
        print("💾 결과 저장: coach_stats_2025_26.json")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        calculator.close()

if __name__ == "__main__":
    main()
