#!/usr/bin/env python3
"""
선수별 최근 폼 스냅샷 생성

L5 (최근 5경기), L10 (최근 10경기), L15 (최근 15경기) 평균 계산
"""

from neo4j import GraphDatabase
from datetime import datetime
from statistics import mean, stdev
import os


class PlayerRecentFormGenerator:
    def __init__(self):
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password123')
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def calculate_trend(self, recent_games):
        """최근 폼 트렌드 계산 (hot/cold/stable)"""
        if len(recent_games) < 3:
            return 'insufficient_data'

        # 최근 3경기 vs 이전 경기 비교
        recent_3 = [g['points'] for g in recent_games[:3]]
        earlier = [g['points'] for g in recent_games[3:]]

        if not earlier:
            return 'stable'

        recent_avg = mean(recent_3)
        earlier_avg = mean(earlier)

        diff_pct = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0

        if diff_pct > 0.15:  # 15% 이상 상승
            return 'hot'
        elif diff_pct < -0.15:  # 15% 이상 하락
            return 'cold'
        else:
            return 'stable'

    def generate_recent_form(self, player_name, period='L5'):
        """특정 선수의 최근 폼 계산"""
        n = int(period[1:])  # 'L5' -> 5

        with self.driver.session() as session:
            # 최근 N경기 조회
            result = session.run("""
                MATCH (p:Player {name: $player_name})-[:PLAYED_IN]->(pb:PlayerBoxScore)
                WHERE pb.minutes > 0
                RETURN pb.points as points,
                       pb.rebounds as rebounds,
                       pb.assists as assists,
                       pb.fg_made as fg_made,
                       pb.fg_attempted as fg_attempted,
                       pb.three_made as three_made,
                       pb.three_attempted as three_attempted,
                       pb.plus_minus as plus_minus,
                       pb.minutes as minutes,
                       pb.date as date
                ORDER BY pb.date DESC
                LIMIT $n
            """, player_name=player_name, n=n)

            games = list(result)

            if len(games) < 3:  # 최소 3경기 필요
                return None

            # 평균 계산
            ppg = mean([g['points'] for g in games])
            rpg = mean([g['rebounds'] for g in games])
            apg = mean([g['assists'] for g in games])
            mpg = mean([g['minutes'] for g in games])
            plus_minus = mean([g['plus_minus'] for g in games])

            # FG%
            total_fg_made = sum([g['fg_made'] for g in games])
            total_fg_att = sum([g['fg_attempted'] for g in games])
            fg_pct = total_fg_made / total_fg_att if total_fg_att > 0 else 0

            # 3PT%
            total_3pt_made = sum([g['three_made'] for g in games])
            total_3pt_att = sum([g['three_attempted'] for g in games])
            three_pct = total_3pt_made / total_3pt_att if total_3pt_att > 0 else 0

            # 트렌드
            trend = self.calculate_trend(games)

            # 일관성 (표준편차)
            consistency = 1 / (stdev([g['points'] for g in games]) + 1) if len(games) > 1 else 1.0

            return {
                'period': period,
                'games_played': len(games),
                'ppg': round(ppg, 1),
                'rpg': round(rpg, 1),
                'apg': round(apg, 1),
                'mpg': round(mpg, 1),
                'fg_pct': round(fg_pct, 3),
                'three_pct': round(three_pct, 3),
                'plus_minus': round(plus_minus, 1),
                'trend': trend,
                'consistency': round(consistency, 3),
                'last_game_date': games[0]['date'].isoformat(),
                'updated_at': datetime.now().isoformat()
            }

    def save_recent_form(self, player_name, form_data):
        """Neo4j에 저장"""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Player {name: $player_name})
                MERGE (p)-[:HAS_RECENT_FORM]->(rf:PlayerRecentForm {period: $period})
                SET rf.games_played = $games_played,
                    rf.ppg = $ppg,
                    rf.rpg = $rpg,
                    rf.apg = $apg,
                    rf.mpg = $mpg,
                    rf.fg_pct = $fg_pct,
                    rf.three_pct = $three_pct,
                    rf.plus_minus = $plus_minus,
                    rf.trend = $trend,
                    rf.consistency = $consistency,
                    rf.last_game_date = date($last_game_date),
                    rf.updated_at = datetime($updated_at)
            """,
                player_name=player_name,
                period=form_data['period'],
                games_played=form_data['games_played'],
                ppg=form_data['ppg'],
                rpg=form_data['rpg'],
                apg=form_data['apg'],
                mpg=form_data['mpg'],
                fg_pct=form_data['fg_pct'],
                three_pct=form_data['three_pct'],
                plus_minus=form_data['plus_minus'],
                trend=form_data['trend'],
                consistency=form_data['consistency'],
                last_game_date=form_data['last_game_date'],
                updated_at=form_data['updated_at']
            )

    def generate_all(self):
        """모든 선수의 최근 폼 생성"""
        with self.driver.session() as session:
            # 활동 중인 선수 목록 (최소 5경기 이상)
            result = session.run("""
                MATCH (p:Player)-[:PLAYED_IN]->(pb:PlayerBoxScore)
                WHERE pb.minutes > 0
                WITH p.name as player, count(pb) as games
                WHERE games >= 5
                RETURN player
                ORDER BY player
            """)

            players = [r['player'] for r in result]

        print(f"총 {len(players)}명 선수 처리 시작")
        print("="*70)

        success_count = 0
        error_count = 0

        for i, player in enumerate(players, 1):
            try:
                print(f"[{i}/{len(players)}] {player:30}", end=' ')

                # L5, L10, L15 생성
                for period in ['L5', 'L10', 'L15']:
                    form_data = self.generate_recent_form(player, period)
                    if form_data:
                        self.save_recent_form(player, form_data)

                print("✅")
                success_count += 1

            except Exception as e:
                print(f"❌ {e}")
                error_count += 1

        print()
        print("="*70)
        print(f"✅ 성공: {success_count}명")
        print(f"❌ 실패: {error_count}명")
        print(f"📊 생성된 노드: {success_count * 3}개 (L5, L10, L15)")


def main():
    generator = PlayerRecentFormGenerator()

    try:
        print("="*70)
        print("PlayerRecentForm 생성 시작")
        print("="*70)
        print()

        generator.generate_all()

        print()
        print("✅ 완료!")

    finally:
        generator.close()


if __name__ == "__main__":
    main()
