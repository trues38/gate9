"""
Enhanced Data Collection for Graph RAG Analysis
수집 가능한 모든 데이터를 추출하고 Neo4j에 통합
"""

import json
import glob
from datetime import datetime, timedelta
from collections import defaultdict
from neo4j import GraphDatabase
import os

class EnhancedDataCollector:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.player_stats = defaultdict(list)
        self.lineup_data = []
        self.formation_data = []
        self.suspension_data = []
        self.fatigue_context = []

    def close(self):
        self.driver.close()

    def collect_player_lineup_data(self):
        """
        match_details.json에서 선수 라인업 및 통계 수집
        """
        print("=" * 60)
        print("1단계: 선수 라인업 및 통계 데이터 수집")
        print("=" * 60)

        detail_files = glob.glob("raw_data/understat/*/202*/match_details.json")

        total_players = 0
        total_matches = 0

        for file_path in detail_files:
            league = file_path.split('/')[-3]
            season = file_path.split('/')[-2]

            with open(file_path, 'r') as f:
                matches = json.load(f)

            for match in matches:
                match_id = match['match_id']
                total_matches += 1

                # 홈팀 라인업
                if 'lineups' in match and 'h' in match['lineups']:
                    for player_id, player_data in match['lineups']['h'].items():
                        total_players += 1
                        self.player_stats[player_data['player']].append({
                            'match_id': match_id,
                            'team_id': player_data['team_id'],
                            'position': player_data['position'],
                            'goals': int(player_data.get('goals', 0)),
                            'assists': int(player_data.get('assists', 0)),
                            'shots': int(player_data.get('shots', 0)),
                            'xG': float(player_data.get('xG', 0)),
                            'xA': float(player_data.get('xA', 0)),
                            'time': int(player_data.get('time', 0)),
                            'yellow_card': int(player_data.get('yellow_card', 0)),
                            'red_card': int(player_data.get('red_card', 0)),
                            'key_passes': int(player_data.get('key_passes', 0)),
                            'h_a': 'h',
                            'league': league,
                            'season': season
                        })

                        # 라인업 데이터 저장
                        self.lineup_data.append({
                            'match_id': match_id,
                            'player_name': player_data['player'],
                            'player_id': player_data['player_id'],
                            'team_id': player_data['team_id'],
                            'position': player_data['position'],
                            'position_order': player_data.get('positionOrder', 0),
                            'time_played': int(player_data.get('time', 0)),
                            'h_a': 'h'
                        })

                        # 징계 기록
                        if int(player_data.get('yellow_card', 0)) > 0 or int(player_data.get('red_card', 0)) > 0:
                            self.suspension_data.append({
                                'match_id': match_id,
                                'player_name': player_data['player'],
                                'yellow': int(player_data.get('yellow_card', 0)),
                                'red': int(player_data.get('red_card', 0))
                            })

                # 원정팀 라인업
                if 'lineups' in match and 'a' in match['lineups']:
                    for player_id, player_data in match['lineups']['a'].items():
                        total_players += 1
                        self.player_stats[player_data['player']].append({
                            'match_id': match_id,
                            'team_id': player_data['team_id'],
                            'position': player_data['position'],
                            'goals': int(player_data.get('goals', 0)),
                            'assists': int(player_data.get('assists', 0)),
                            'shots': int(player_data.get('shots', 0)),
                            'xG': float(player_data.get('xG', 0)),
                            'xA': float(player_data.get('xA', 0)),
                            'time': int(player_data.get('time', 0)),
                            'yellow_card': int(player_data.get('yellow_card', 0)),
                            'red_card': int(player_data.get('red_card', 0)),
                            'key_passes': int(player_data.get('key_passes', 0)),
                            'h_a': 'a',
                            'league': league,
                            'season': season
                        })

                        self.lineup_data.append({
                            'match_id': match_id,
                            'player_name': player_data['player'],
                            'player_id': player_data['player_id'],
                            'team_id': player_data['team_id'],
                            'position': player_data['position'],
                            'position_order': player_data.get('positionOrder', 0),
                            'time_played': int(player_data.get('time', 0)),
                            'h_a': 'a'
                        })

                        if int(player_data.get('yellow_card', 0)) > 0 or int(player_data.get('red_card', 0)) > 0:
                            self.suspension_data.append({
                                'match_id': match_id,
                                'player_name': player_data['player'],
                                'yellow': int(player_data.get('yellow_card', 0)),
                                'red': int(player_data.get('red_card', 0))
                            })

        print(f"✅ 수집 완료:")
        print(f"   - 경기 수: {total_matches}")
        print(f"   - 총 선수 출전 기록: {total_players}")
        print(f"   - 고유 선수 수: {len(self.player_stats)}")
        print(f"   - 징계 기록: {len(self.suspension_data)}")
        print()

    def analyze_formations(self):
        """
        포지션 데이터로부터 포메이션 추론
        """
        print("=" * 60)
        print("2단계: 포메이션 분석")
        print("=" * 60)

        match_formations = defaultdict(lambda: {'h': [], 'a': []})

        for lineup in self.lineup_data:
            match_id = lineup['match_id']
            side = lineup['h_a']
            position = lineup['position']

            if lineup['time_played'] >= 45:  # 최소 45분 출전
                match_formations[match_id][side].append(position)

        for match_id, formations in match_formations.items():
            h_formation = self._infer_formation(formations['h'])
            a_formation = self._infer_formation(formations['a'])

            if h_formation and a_formation:
                self.formation_data.append({
                    'match_id': match_id,
                    'home_formation': h_formation,
                    'away_formation': a_formation
                })

        print(f"✅ 포메이션 분석 완료:")
        print(f"   - 분석된 경기 수: {len(self.formation_data)}")

        # 가장 흔한 포메이션
        from collections import Counter
        h_formations = Counter([f['home_formation'] for f in self.formation_data])
        a_formations = Counter([f['away_formation'] for f in self.formation_data])

        print(f"   - 가장 흔한 홈 포메이션: {h_formations.most_common(3)}")
        print(f"   - 가장 흔한 원정 포메이션: {a_formations.most_common(3)}")
        print()

    def _infer_formation(self, positions):
        """
        포지션 리스트로부터 포메이션 추론 (예: 4-3-3, 4-4-2)
        """
        if not positions:
            return None

        defenders = sum(1 for p in positions if p in ['DL', 'DR', 'DC', 'D'])
        midfielders = sum(1 for p in positions if p in ['ML', 'MR', 'MC', 'M', 'AMC', 'DMC'])
        forwards = sum(1 for p in positions if p in ['FW', 'FWL', 'FWR', 'F'])

        # GK는 제외
        if defenders == 0 or forwards == 0:
            return None

        return f"{defenders}-{midfielders}-{forwards}"

    def calculate_fatigue_context(self):
        """
        경기 일정으로부터 피로도 컨텍스트 계산
        """
        print("=" * 60)
        print("3단계: 피로도 컨텍스트 분석")
        print("=" * 60)

        # results.json에서 경기 날짜 로드
        results_files = glob.glob("raw_data/understat/*/202*/results.json")

        team_schedule = defaultdict(list)

        for file_path in results_files:
            with open(file_path, 'r') as f:
                matches = json.load(f)

            for match in matches:
                date = datetime.fromisoformat(match['datetime'].replace('Z', '+00:00'))
                h_team = match['h']['title']
                a_team = match['a']['title']

                team_schedule[h_team].append({
                    'date': date,
                    'match_id': match['id'],
                    'h_a': 'h'
                })
                team_schedule[a_team].append({
                    'date': date,
                    'match_id': match['id'],
                    'h_a': 'a'
                })

        # 각 팀의 일정 정렬
        for team in team_schedule:
            team_schedule[team].sort(key=lambda x: x['date'])

        # 피로도 컨텍스트 계산
        for team, schedule in team_schedule.items():
            for i, match in enumerate(schedule):
                if i == 0:
                    continue

                prev_match = schedule[i-1]
                days_rest = (match['date'] - prev_match['date']).days

                # 최근 7일간 경기 수
                recent_matches = sum(1 for m in schedule[:i]
                                    if (match['date'] - m['date']).days <= 7)

                self.fatigue_context.append({
                    'match_id': match['match_id'],
                    'team': team,
                    'days_rest': days_rest,
                    'matches_last_7days': recent_matches,
                    'is_congested': 1 if days_rest <= 3 or recent_matches >= 3 else 0
                })

        print(f"✅ 피로도 분석 완료:")
        print(f"   - 분석된 팀-경기 조합: {len(self.fatigue_context)}")

        if len(self.fatigue_context) > 0:
            congested = sum(1 for f in self.fatigue_context if f['is_congested'])
            print(f"   - 일정 과밀 경기: {congested} ({congested/len(self.fatigue_context)*100:.1f}%)")
        print()

    def calculate_player_form(self):
        """
        선수별 최근 폼 계산 (최근 5경기 골/어시스트)
        """
        print("=" * 60)
        print("4단계: 선수 폼 분석")
        print("=" * 60)

        player_form = {}

        for player, matches in self.player_stats.items():
            # 경기를 match_id 순으로 정렬 (시간순)
            sorted_matches = sorted(matches, key=lambda x: x['match_id'])

            recent_5_goals = 0
            recent_5_assists = 0
            recent_5_xg = 0.0
            recent_5_minutes = 0

            if len(sorted_matches) >= 5:
                last_5 = sorted_matches[-5:]
                recent_5_goals = sum(m['goals'] for m in last_5)
                recent_5_assists = sum(m['assists'] for m in last_5)
                recent_5_xg = sum(m['xG'] for m in last_5)
                recent_5_minutes = sum(m['time'] for m in last_5)

            # 전체 통계
            total_goals = sum(m['goals'] for m in sorted_matches)
            total_assists = sum(m['assists'] for m in sorted_matches)
            total_xg = sum(m['xG'] for m in sorted_matches)
            total_minutes = sum(m['time'] for m in sorted_matches)
            total_matches = len(sorted_matches)

            player_form[player] = {
                'total_matches': total_matches,
                'total_goals': total_goals,
                'total_assists': total_assists,
                'total_xG': total_xg,
                'total_minutes': total_minutes,
                'recent_5_goals': recent_5_goals,
                'recent_5_assists': recent_5_assists,
                'recent_5_xG': recent_5_xg,
                'recent_5_minutes': recent_5_minutes,
                'goals_per_90': (total_goals / total_minutes * 90) if total_minutes > 0 else 0,
                'assists_per_90': (total_assists / total_minutes * 90) if total_minutes > 0 else 0,
                'primary_position': max(set(m['position'] for m in sorted_matches),
                                       key=[m['position'] for m in sorted_matches].count)
            }

        # 상위 득점자
        top_scorers = sorted(player_form.items(),
                            key=lambda x: x[1]['total_goals'],
                            reverse=True)[:10]

        print(f"✅ 선수 폼 분석 완료:")
        print(f"   - 분석된 선수 수: {len(player_form)}")
        print(f"\n   상위 득점자:")
        for i, (player, stats) in enumerate(top_scorers, 1):
            print(f"   {i}. {player}: {stats['total_goals']}골 "
                  f"({stats['total_matches']}경기, {stats['goals_per_90']:.2f}/90분)")
        print()

        return player_form

    def save_to_neo4j(self, player_form):
        """
        수집한 모든 데이터를 Neo4j에 저장
        """
        print("=" * 60)
        print("5단계: Neo4j에 데이터 저장")
        print("=" * 60)

        with self.driver.session() as session:
            # 1. Player 노드 생성
            print("Player 노드 생성 중...")
            for player, stats in player_form.items():
                session.run("""
                    MERGE (p:Player {name: $name})
                    SET p.total_matches = $total_matches,
                        p.total_goals = $total_goals,
                        p.total_assists = $total_assists,
                        p.total_xG = $total_xG,
                        p.goals_per_90 = $goals_per_90,
                        p.assists_per_90 = $assists_per_90,
                        p.primary_position = $position,
                        p.recent_5_goals = $recent_5_goals,
                        p.recent_5_assists = $recent_5_assists
                """, name=player, **stats)

            print(f"✅ {len(player_form)} Player 노드 생성 완료")

            # 2. Formation 속성 추가
            print("Formation 데이터 추가 중...")
            for formation in self.formation_data:
                session.run("""
                    MATCH (m:Match {match_id: $match_id})
                    SET m.home_formation = $home_formation,
                        m.away_formation = $away_formation
                """, **formation)

            print(f"✅ {len(self.formation_data)} 경기에 포메이션 추가 완료")

            # 3. Fatigue 컨텍스트 추가
            print("피로도 컨텍스트 추가 중...")
            for fatigue in self.fatigue_context:
                session.run("""
                    MATCH (m:Match {match_id: $match_id})
                    MATCH (t:Team {name: $team})
                    MERGE (t)-[r:FATIGUE_CONTEXT]->(m)
                    SET r.days_rest = $days_rest,
                        r.matches_last_7days = $matches_last_7days,
                        r.is_congested = $is_congested
                """, **fatigue)

            print(f"✅ {len(self.fatigue_context)} 피로도 컨텍스트 추가 완료")

            # 4. Player-Match 관계 생성 (라인업)
            print("Player-Match 관계 생성 중...")
            lineup_count = 0
            for lineup in self.lineup_data:
                session.run("""
                    MATCH (p:Player {name: $player_name})
                    MATCH (m:Match {match_id: $match_id})
                    MERGE (p)-[r:PLAYED_IN]->(m)
                    SET r.position = $position,
                        r.time_played = $time_played,
                        r.home_away = $h_a
                """, **lineup)
                lineup_count += 1

            print(f"✅ {lineup_count} Player-Match 관계 생성 완료")

            # 5. Suspension 데이터 추가
            print("징계 기록 추가 중...")
            for suspension in self.suspension_data:
                session.run("""
                    MATCH (p:Player {name: $player_name})
                    MATCH (m:Match {match_id: $match_id})
                    MERGE (p)-[r:DISCIPLINARY_RECORD]->(m)
                    SET r.yellow_cards = $yellow,
                        r.red_cards = $red
                """, **suspension)

            print(f"✅ {len(self.suspension_data)} 징계 기록 추가 완료")

        print("\n" + "=" * 60)
        print("모든 데이터 Neo4j 저장 완료!")
        print("=" * 60)

    def save_processed_data(self, player_form):
        """
        처리된 데이터를 JSON으로 저장 (Graph RAG 분석용)
        """
        print("\n처리된 데이터 JSON 저장 중...")

        # Player form 데이터
        with open('processed/player_form.json', 'w') as f:
            json.dump(player_form, f, indent=2)

        # Formation 데이터
        with open('processed/formation_data.json', 'w') as f:
            json.dump(self.formation_data, f, indent=2)

        # Fatigue 데이터
        with open('processed/fatigue_context.json', 'w') as f:
            json.dump(self.fatigue_context, f, indent=2)

        # Suspension 데이터
        with open('processed/suspension_data.json', 'w') as f:
            json.dump(self.suspension_data, f, indent=2)

        print("✅ 모든 처리 데이터 JSON 저장 완료")
        print(f"   - processed/player_form.json")
        print(f"   - processed/formation_data.json")
        print(f"   - processed/fatigue_context.json")
        print(f"   - processed/suspension_data.json")

def main():
    # Neo4j 연결 정보
    NEO4J_URI = "bolt://localhost:7688"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "00000000")

    collector = EnhancedDataCollector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        # 데이터 수집
        collector.collect_player_lineup_data()
        collector.analyze_formations()
        collector.calculate_fatigue_context()
        player_form = collector.calculate_player_form()

        # JSON 파일로 먼저 저장
        collector.save_processed_data(player_form)

        # Neo4j에 저장 (선택적)
        try:
            print("\nNeo4j 연결 시도 중...")
            collector.save_to_neo4j(player_form)
        except Exception as e:
            print(f"⚠️  Neo4j 저장 실패 (선택적 기능): {str(e)}")
            print("    → JSON 파일로는 저장 완료됨")

        print("\n" + "=" * 60)
        print("🎉 모든 데이터 수집 및 저장 완료!")
        print("=" * 60)
        print("\n다음 단계: Graph RAG 분석 실행")
        print("  python3 graph_rag_analysis.py")

    finally:
        collector.close()

if __name__ == "__main__":
    main()
