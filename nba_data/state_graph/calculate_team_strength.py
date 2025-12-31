#!/usr/bin/env python3
"""
동적 팀 계산 엔진 (v2.0)

Team 노드 없이 실시간 계산:
  Team Strength = Coach + Players + Lineup + Context

사용법:
  from calculate_team_strength import TeamStrengthCalculator, GameContext

  calculator = TeamStrengthCalculator()
  context = GameContext(
      home_team="HOU",
      away_team="OKC",
      home_back_to_back=False,
      away_back_to_back=True,
      home_injuries=[],
      away_injuries=["Chet Holmgren"]
  )

  result = calculator.calculate_matchup(context)
"""

from neo4j import GraphDatabase
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class GameContext:
    """경기 컨텍스트"""
    home_team: str
    away_team: str
    home_back_to_back: bool = False
    away_back_to_back: bool = False
    home_injuries: List[str] = None
    away_injuries: List[str] = None
    referee_home_bias: float = 0.5  # 0.5 = 중립
    altitude: int = 0

    def __post_init__(self):
        if self.home_injuries is None:
            self.home_injuries = []
        if self.away_injuries is None:
            self.away_injuries = []

class TeamStrengthCalculator:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_coach(self, team: str) -> Optional[Dict]:
        """Coach 데이터 가져오기"""

        query = """
        MATCH (coach:Coach {team: $team, season: "2025-26"})
        RETURN coach
        """

        with self.driver.session() as session:
            result = session.run(query, team=team).single()
            if not result:
                return None
            return dict(result['coach'])

    def get_lineup(self, team: str, lineup_name: str = None) -> Optional[Dict]:
        """Lineup 데이터 가져오기"""

        if lineup_name:
            query = """
            MATCH (lineup:Lineup {team: $team, name: $name})
            RETURN lineup
            """
            with self.driver.session() as session:
                result = session.run(query, team=team, name=lineup_name).single()
        else:
            # 기본: usage_pct가 가장 높은 라인업
            query = """
            MATCH (lineup:Lineup {team: $team})
            RETURN lineup
            ORDER BY lineup.usage_pct DESC
            LIMIT 1
            """
            with self.driver.session() as session:
                result = session.run(query, team=team).single()

        if not result:
            return None

        lineup = dict(result['lineup'])

        # Players 데이터 가져오기
        query_players = """
        MATCH (lineup:Lineup {lineup_id: $lineup_id})-[:INCLUDES]->(p:Player)
        RETURN p
        """

        with self.driver.session() as session:
            players_result = session.run(query_players, lineup_id=lineup['lineup_id'])
            lineup['player_objects'] = [dict(record['p']) for record in players_result]

        return lineup

    def get_player(self, player_name: str) -> Optional[Dict]:
        """Player 데이터 가져오기"""

        query = """
        MATCH (p:Player {name: $name})
        RETURN p
        """

        with self.driver.session() as session:
            result = session.run(query, name=player_name).single()
            if not result:
                return None
            return dict(result['p'])

    def calculate_team_strength(
        self,
        team: str,
        context: GameContext,
        lineup_name: str = None
    ) -> Dict:
        """
        팀 강도 동적 계산

        Returns:
          {
              'strength': float,
              'breakdown': {
                  'player_impact': float,
                  'lineup_bonus': float,
                  'context_mod': float,
                  'injury_penalty': float,
                  'tempo_factor': float
              }
          }
        """

        # 1. Coach 기본값
        coach = self.get_coach(team)
        if not coach:
            return {'strength': 0, 'breakdown': {}, 'error': f'Coach not found for {team}'}

        base_tempo = coach.get('tempo', 100)
        rotation_depth = coach.get('rotation_depth', 7)
        rotation_fatigue = rotation_depth / 10  # 로테이션 깊을수록 피로 적음

        # 2. Lineup 선택
        lineup = self.get_lineup(team, lineup_name)
        if not lineup:
            return {'strength': 0, 'breakdown': {}, 'error': f'Lineup not found for {team}'}

        players = lineup.get('player_objects', [])
        if not players:
            return {'strength': 0, 'breakdown': {}, 'error': f'No players in lineup for {team}'}

        # 3. Player Impact 합산
        total_impact = sum(p.get('avg_plus_minus', 0) for p in players)

        # 4. Lineup 시너지 (사용자 입력)
        offense_rating = lineup.get('offense_rating', 1.0)
        defense_rating = lineup.get('defense_rating', 1.0)
        lineup_bonus = (offense_rating + defense_rating - 2) * 5  # -5 ~ +5 범위

        # 5. Context 조정
        context_mod = 0

        # 홈/원정
        is_home = (team == context.home_team)
        is_back_to_back = context.home_back_to_back if is_home else context.away_back_to_back

        # 백투백 페널티
        if is_back_to_back:
            # 로테이션 깊이에 따라 페널티 달라짐
            fatigue_penalty = -15 * (1 - rotation_fatigue)

            # 선수별 stamina 고려
            stamina_avg = sum(p.get('stamina', 0.95) for p in players) / len(players)
            fatigue_penalty *= (2 - stamina_avg)

            context_mod += fatigue_penalty

        # 홈 어드밴티지
        if is_home:
            context_mod += 3
            if context.referee_home_bias > 0.55:
                context_mod += 2

        # 고지대
        if is_home and context.altitude > 1000:
            context_mod += 1

        # 6. 부상자 영향
        injury_penalty = 0
        injuries = context.home_injuries if is_home else context.away_injuries

        for injured_player in injuries:
            p = self.get_player(injured_player)
            if p:
                injury_penalty -= p.get('avg_plus_minus', 0)

        # 7. 템포 조정
        tempo_boost = lineup.get('tempo_boost', 1.0)
        tempo_factor = (base_tempo * tempo_boost - 100) * 0.3

        # 최종 계산
        team_strength = (
            total_impact +          # 선수 개인 능력
            lineup_bonus +          # 라인업 시너지
            context_mod +           # 백투백, 홈, 심판
            injury_penalty +        # 부상자
            tempo_factor            # 템포
        )

        return {
            'strength': round(team_strength, 1),
            'breakdown': {
                'player_impact': round(total_impact, 1),
                'lineup_bonus': round(lineup_bonus, 1),
                'context': round(context_mod, 1),
                'injuries': round(injury_penalty, 1),
                'tempo': round(tempo_factor, 1)
            },
            'lineup': lineup['name'],
            'coach': coach.get('name', '?'),
            'rotation_depth': rotation_depth,
            'players': [p['name'] for p in players]
        }

    def calculate_matchup(
        self,
        context: GameContext,
        home_lineup: str = None,
        away_lineup: str = None
    ) -> Dict:
        """
        양 팀 매치업 계산

        Returns:
          {
              'home': {...},
              'away': {...},
              'differential': float,
              'predicted_winner': str
          }
        """

        home_result = self.calculate_team_strength(context.home_team, context, home_lineup)
        away_result = self.calculate_team_strength(context.away_team, context, away_lineup)

        differential = home_result['strength'] - away_result['strength']
        predicted_winner = context.home_team if differential > 0 else context.away_team

        return {
            'home': home_result,
            'away': away_result,
            'differential': round(differential, 1),
            'predicted_winner': predicted_winner,
            'confidence': abs(differential)
        }

    def simulate_injury(
        self,
        team: str,
        injured_player: str,
        context: GameContext,
        lineup_name: str = None
    ) -> Dict:
        """부상자 시뮬레이션"""

        # 정상 팀
        normal_context = GameContext(
            home_team=context.home_team,
            away_team=context.away_team,
            home_back_to_back=context.home_back_to_back,
            away_back_to_back=context.away_back_to_back,
            home_injuries=[] if team == context.home_team else context.home_injuries,
            away_injuries=[] if team == context.away_team else context.away_injuries
        )
        normal = self.calculate_team_strength(team, normal_context, lineup_name)

        # 부상자 있는 팀
        injured_context = GameContext(
            home_team=context.home_team,
            away_team=context.away_team,
            home_back_to_back=context.home_back_to_back,
            away_back_to_back=context.away_back_to_back,
            home_injuries=[injured_player] if team == context.home_team else context.home_injuries,
            away_injuries=[injured_player] if team == context.away_team else context.away_injuries
        )
        injured = self.calculate_team_strength(team, injured_context, lineup_name)

        diff = injured['strength'] - normal['strength']

        return {
            'player': injured_player,
            'normal_strength': normal['strength'],
            'injured_strength': injured['strength'],
            'difference': round(diff, 1),
            'impact_pct': round((diff / normal['strength']) * 100, 1) if normal['strength'] != 0 else 0
        }

def main():
    """테스트"""

    calculator = TeamStrengthCalculator()

    try:
        print("=" * 80)
        print("동적 팀 계산 엔진 테스트 (v2.0)")
        print("=" * 80)
        print()

        # 테스트 1: OKC vs OKC (기본 라인업)
        print("테스트 1: OKC 팀 강도 계산")
        print("-" * 80)

        context = GameContext(
            home_team="OKC",
            away_team="LAL",
            home_back_to_back=False
        )

        result = calculator.calculate_team_strength("OKC", context)

        print(f"팀: OKC")
        print(f"코치: {result['coach']}")
        print(f"라인업: {result['lineup']}")
        print(f"선수: {', '.join(result['players'])}")
        print()
        print(f"총 강도: {result['strength']}")
        print(f"분석:")
        for key, value in result['breakdown'].items():
            print(f"  - {key}: {value:+.1f}")
        print()

        # 테스트 2: 백투백 영향
        print("테스트 2: 백투백 영향 비교")
        print("-" * 80)

        context_normal = GameContext(home_team="OKC", away_team="LAL", home_back_to_back=False)
        context_b2b = GameContext(home_team="OKC", away_team="LAL", home_back_to_back=True)

        normal = calculator.calculate_team_strength("OKC", context_normal)
        b2b = calculator.calculate_team_strength("OKC", context_b2b)

        print(f"정상: {normal['strength']}")
        print(f"백투백: {b2b['strength']}")
        print(f"차이: {b2b['strength'] - normal['strength']:+.1f}")
        print()

        # 테스트 3: 부상자 시뮬레이션 (if Adams lineup exists)
        print("테스트 3: 선수 부상 시뮬레이션")
        print("-" * 80)

        # OKC의 핵심 선수로 시뮬레이션
        sim_context = GameContext(home_team="OKC", away_team="LAL")
        sim = calculator.simulate_injury("OKC", "Shai Gilgeous-Alexander", sim_context)

        print(f"선수: {sim['player']}")
        print(f"정상 강도: {sim['normal_strength']}")
        print(f"부상 시 강도: {sim['injured_strength']}")
        print(f"차이: {sim['difference']:+.1f} ({sim['impact_pct']:+.1f}%)")
        print()

        calculator.close()

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        calculator.close()

if __name__ == "__main__":
    main()
