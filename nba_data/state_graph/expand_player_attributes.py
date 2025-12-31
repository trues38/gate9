#!/usr/bin/env python3
"""
Player 속성 확장 (v2.0)

PlayerBoxScore 데이터에서 선수 속성 계산:
- Impact (avg_plus_minus, impact_percentile)
- Usage (avg_minutes, games_played/missed, injury_prone)
- Stats (ppg, rpg, apg, oreb_pg, spg, bpg)
- Stamina (백투백 성능 하락)
- Style Tags (자동 분류)

25-26 시즌 데이터 기반
"""

from neo4j import GraphDatabase
from typing import Dict, List, Optional
import json
from collections import defaultdict

class PlayerAttributeExpander:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_all_players(self, season_start='2025-10-01') -> List[Dict]:
        """25-26 시즌에 출전한 모든 선수 리스트"""

        query = """
        MATCH (pb:PlayerBoxScore)
        WHERE pb.date >= date($season_start)
        RETURN DISTINCT pb.player_name AS name, pb.team AS team, pb.position AS position
        ORDER BY pb.team, pb.player_name
        """

        with self.driver.session() as session:
            result = session.run(query, season_start=season_start)
            return [dict(record) for record in result]

    def calculate_player_stats(self, player_name: str, season_start='2025-10-01') -> Optional[Dict]:
        """선수 기본 통계 계산"""

        query = """
        MATCH (pb:PlayerBoxScore)
        WHERE pb.player_name = $name
          AND pb.date >= date($season_start)
          AND pb.minutes IS NOT NULL
          AND pb.minutes > 0
        WITH pb
        ORDER BY pb.date
        RETURN
          avg(pb.plus_minus) AS avg_plus_minus,
          avg(pb.minutes) AS avg_minutes,
          avg(pb.points) AS ppg,
          avg(pb.rebounds) AS rpg,
          avg(pb.assists) AS apg,
          avg(pb.steals) AS spg,
          avg(pb.blocks) AS bpg,
          avg(pb.off_rebounds) AS oreb_pg,
          avg(pb.def_rebounds) AS dreb_pg,
          avg(pb.turnovers) AS tpg,
          avg(pb.fouls) AS fpg,
          avg(pb.fg_made * 1.0 / CASE WHEN pb.fg_attempted > 0 THEN pb.fg_attempted ELSE 1 END) AS fg_pct,
          avg(pb.three_made * 1.0 / CASE WHEN pb.three_attempted > 0 THEN pb.three_attempted ELSE 1 END) AS three_pct,
          avg(pb.ft_made * 1.0 / CASE WHEN pb.ft_attempted > 0 THEN pb.ft_attempted ELSE 1 END) AS ft_pct,
          count(*) AS games_played,
          collect(pb.date) AS dates
        """

        with self.driver.session() as session:
            result = session.run(query, name=player_name, season_start=season_start).single()

            if not result or result['games_played'] == 0:
                return None

            return {
                'avg_plus_minus': round(result['avg_plus_minus'], 1) if result['avg_plus_minus'] is not None else 0,
                'avg_minutes': round(result['avg_minutes'], 1) if result['avg_minutes'] else 0,
                'ppg': round(result['ppg'], 1) if result['ppg'] else 0,
                'rpg': round(result['rpg'], 1) if result['rpg'] else 0,
                'apg': round(result['apg'], 1) if result['apg'] else 0,
                'spg': round(result['spg'], 1) if result['spg'] else 0,
                'bpg': round(result['bpg'], 1) if result['bpg'] else 0,
                'oreb_pg': round(result['oreb_pg'], 1) if result['oreb_pg'] else 0,
                'dreb_pg': round(result['dreb_pg'], 1) if result['dreb_pg'] else 0,
                'tpg': round(result['tpg'], 1) if result['tpg'] else 0,
                'fpg': round(result['fpg'], 1) if result['fpg'] else 0,
                'fg_pct': round(result['fg_pct'], 3) if result['fg_pct'] else 0,
                'three_pct': round(result['three_pct'], 3) if result['three_pct'] else 0,
                'ft_pct': round(result['ft_pct'], 3) if result['ft_pct'] else 0,
                'games_played': result['games_played'],
                'dates': result['dates']
            }

    def calculate_stamina(self, player_name: str, team: str, season_start='2025-10-01') -> float:
        """
        백투백 체력 계산
        stamina = 1 - (abs(b2b_plus_minus_drop) / 10)
        """

        query = """
        MATCH (g1:GameState)-[:HAS_BOXSCORE]->(pb1:PlayerBoxScore)
        MATCH (g2:GameState)-[:HAS_BOXSCORE]->(pb2:PlayerBoxScore)
        WHERE pb1.player_name = $name
          AND pb2.player_name = $name
          AND pb1.team = $team
          AND pb2.team = $team
          AND g1.date >= date($season_start)
          AND g2.date = date(g1.date) + duration('P1D')
          AND pb1.minutes > 10
          AND pb2.minutes > 10
        RETURN avg(pb2.plus_minus - pb1.plus_minus) AS fatigue_drop,
               count(*) AS b2b_count
        """

        with self.driver.session() as session:
            result = session.run(query, name=player_name, team=team, season_start=season_start).single()

            if not result or result['b2b_count'] == 0:
                return 0.95  # 기본값 (백투백 데이터 없음)

            fatigue_drop = result['fatigue_drop'] if result['fatigue_drop'] is not None else 0
            stamina = 1 - (abs(fatigue_drop) / 10)
            return round(max(0.5, min(1.0, stamina)), 2)  # 0.5 ~ 1.0 범위

    def calculate_injury_rate(self, team: str, dates: List, season_start='2025-10-01') -> Dict:
        """결장 경기 계산"""

        # 팀 전체 경기 수
        query = """
        MATCH (g:GameState)
        WHERE (g.home_team = $team OR g.away_team = $team)
          AND g.date >= date($season_start)
        RETURN count(*) AS team_games
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, season_start=season_start).single()
            team_games = result['team_games'] if result else 0

            if team_games == 0:
                return {'games_missed': 0, 'injury_prone': 0}

            games_played = len(dates)
            games_missed = team_games - games_played

            return {
                'games_missed': games_missed,
                'injury_prone': round(games_missed / team_games, 2) if team_games > 0 else 0
            }

    def classify_style_tags(self, stats: Dict) -> List[str]:
        """스탯 기반 스타일 태그 자동 분류"""

        tags = []

        # 득점
        if stats['ppg'] >= 25:
            tags.append('superstar-scorer')
        elif stats['ppg'] >= 20:
            tags.append('primary-scorer')
        elif stats['ppg'] >= 15:
            tags.append('secondary-scorer')

        # 리바운드
        if stats['rpg'] >= 10:
            tags.append('elite-rebounder')
        if stats['oreb_pg'] >= 3.0:
            tags.append('oreb-specialist')

        # 어시스트
        if stats['apg'] >= 8:
            tags.append('elite-playmaker')
        elif stats['apg'] >= 6:
            tags.append('playmaker')

        # 수비
        if stats['bpg'] >= 1.5:
            tags.append('rim-protector')
        if stats['spg'] >= 1.5:
            tags.append('perimeter-defender')

        # 출전 시간
        if stats['avg_minutes'] >= 35:
            tags.append('workhorse')
        elif stats['avg_minutes'] < 15:
            tags.append('bench-role')

        # 효율
        if stats['fg_pct'] >= 0.55:
            tags.append('efficient-finisher')
        if stats['three_pct'] >= 0.40 and stats['ppg'] >= 10:
            tags.append('three-point-specialist')

        # 턴오버
        if stats['tpg'] >= 3.0:
            tags.append('turnover-prone')

        return tags

    def calculate_impact_percentile(self, player_plus_minus: float, all_players_plus_minus: List[float]) -> float:
        """리그 내 Impact 순위 (percentile)"""

        if not all_players_plus_minus:
            return 0.5

        sorted_plus_minus = sorted(all_players_plus_minus)
        rank = sum(1 for pm in sorted_plus_minus if pm < player_plus_minus)
        percentile = rank / len(sorted_plus_minus)

        return round(percentile, 2)

    def update_player_node(self, player_name: str, team: str, position: str, attributes: Dict):
        """Player 노드 속성 업데이트"""

        query = """
        MERGE (p:Player {name: $name})
        SET p.team = $team,
            p.position = $position,
            p.season = $season,
            p.avg_plus_minus = $avg_plus_minus,
            p.impact_percentile = $impact_percentile,
            p.avg_minutes = $avg_minutes,
            p.games_played = $games_played,
            p.games_missed = $games_missed,
            p.injury_prone = $injury_prone,
            p.ppg = $ppg,
            p.rpg = $rpg,
            p.apg = $apg,
            p.spg = $spg,
            p.bpg = $bpg,
            p.oreb_pg = $oreb_pg,
            p.dreb_pg = $dreb_pg,
            p.tpg = $tpg,
            p.fpg = $fpg,
            p.fg_pct = $fg_pct,
            p.three_pct = $three_pct,
            p.ft_pct = $ft_pct,
            p.stamina = $stamina,
            p.style_tags = $style_tags,
            p.updated_at = datetime()
        RETURN p
        """

        with self.driver.session() as session:
            session.run(query,
                name=player_name,
                team=team,
                position=position,
                season="2025-26",
                avg_plus_minus=attributes.get('avg_plus_minus', 0),
                impact_percentile=attributes.get('impact_percentile', 0.5),
                avg_minutes=attributes.get('avg_minutes', 0),
                games_played=attributes.get('games_played', 0),
                games_missed=attributes.get('games_missed', 0),
                injury_prone=attributes.get('injury_prone', 0),
                ppg=attributes.get('ppg', 0),
                rpg=attributes.get('rpg', 0),
                apg=attributes.get('apg', 0),
                spg=attributes.get('spg', 0),
                bpg=attributes.get('bpg', 0),
                oreb_pg=attributes.get('oreb_pg', 0),
                dreb_pg=attributes.get('dreb_pg', 0),
                tpg=attributes.get('tpg', 0),
                fpg=attributes.get('fpg', 0),
                fg_pct=attributes.get('fg_pct', 0),
                three_pct=attributes.get('three_pct', 0),
                ft_pct=attributes.get('ft_pct', 0),
                stamina=attributes.get('stamina', 0.95),
                style_tags=attributes.get('style_tags', [])
            )

    def process_all_players(self, season_start='2025-10-01'):
        """모든 선수 속성 확장"""

        print("=" * 80)
        print("Player 속성 확장 (v2.0)")
        print("=" * 80)
        print(f"시즌: 2025-26 (from {season_start})")
        print()

        # 모든 선수 가져오기
        players = self.get_all_players(season_start)
        print(f"총 선수: {len(players)}명")
        print()

        # 1차: 모든 선수 스탯 계산 (impact percentile 계산용)
        print("1단계: 선수 스탯 계산 중...")
        player_stats = {}
        all_plus_minus = []

        for player in players:
            stats = self.calculate_player_stats(player['name'], season_start)
            if stats:
                player_stats[player['name']] = {**player, **stats}
                all_plus_minus.append(stats['avg_plus_minus'])

        print(f"  ✅ {len(player_stats)}명 스탯 계산 완료")
        print()

        # 2단계: 확장 속성 계산 및 저장
        print("2단계: 확장 속성 계산 및 Neo4j 업데이트 중...")
        results = []
        count = 0

        for player_name, player_data in player_stats.items():
            count += 1

            # Impact percentile
            impact_percentile = self.calculate_impact_percentile(
                player_data['avg_plus_minus'],
                all_plus_minus
            )

            # Stamina
            stamina = self.calculate_stamina(player_name, player_data['team'], season_start)

            # 결장 경기
            injury_data = self.calculate_injury_rate(
                player_data['team'],
                player_data['dates'],
                season_start
            )

            # Style tags
            style_tags = self.classify_style_tags(player_data)

            # 통합
            attributes = {
                **player_data,
                'impact_percentile': impact_percentile,
                'stamina': stamina,
                **injury_data,
                'style_tags': style_tags
            }

            # Neo4j 업데이트
            self.update_player_node(
                player_name,
                player_data['team'],
                player_data['position'],
                attributes
            )

            # 진행 상황 출력 (10명마다)
            if count % 50 == 0:
                print(f"  진행: {count}/{len(player_stats)}명...")

            # JSON 저장용 (dates 제외)
            attributes_for_json = {k: v for k, v in attributes.items() if k != 'dates'}

            results.append({
                'name': player_name,
                'team': player_data['team'],
                'attributes': attributes_for_json
            })

        print(f"  ✅ {len(results)}명 속성 확장 완료")
        print()

        print("=" * 80)
        print(f"✅ Player 노드 확장 완료")
        print("=" * 80)
        print()

        # 통계
        print("📊 주요 선수 통계:")
        print()

        # Top scorers
        print("득점왕 (Top 10):")
        sorted_by_ppg = sorted(results, key=lambda x: x['attributes']['ppg'], reverse=True)
        for i, r in enumerate(sorted_by_ppg[:10], 1):
            a = r['attributes']
            tags = ', '.join(a['style_tags'][:2]) if a['style_tags'] else ''
            print(f"  {i:2d}. {r['name']:25s} ({r['team']}) - {a['ppg']}ppg, {a['rpg']}rpg, {a['apg']}apg [{tags}]")

        print()

        # Top impact
        print("Impact 순위 (Top 10, +/- 기준):")
        sorted_by_impact = sorted(results, key=lambda x: x['attributes']['avg_plus_minus'], reverse=True)
        for i, r in enumerate(sorted_by_impact[:10], 1):
            a = r['attributes']
            print(f"  {i:2d}. {r['name']:25s} ({r['team']}) - +/- {a['avg_plus_minus']:+.1f} (percentile {a['impact_percentile']:.0%})")

        print()

        # Oreb specialists
        print("오펜스 리바운드 전문가 (Top 10):")
        sorted_by_oreb = sorted(results, key=lambda x: x['attributes']['oreb_pg'], reverse=True)
        for i, r in enumerate(sorted_by_oreb[:10], 1):
            a = r['attributes']
            print(f"  {i:2d}. {r['name']:25s} ({r['team']}) - {a['oreb_pg']}개/경기 (총 {a['rpg']}rpg)")

        return results

def main():
    expander = PlayerAttributeExpander()

    try:
        results = expander.process_all_players()

        # 결과 저장
        with open('player_attributes_2025_26.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print()
        print("💾 결과 저장: player_attributes_2025_26.json")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        expander.close()

if __name__ == "__main__":
    main()
