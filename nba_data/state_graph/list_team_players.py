#!/usr/bin/env python3
"""
팀별 선수 리스트 출력

Lineup 작성 시 정확한 선수 이름 확인용

사용법:
  python list_team_players.py HOU
  python list_team_players.py --all
"""

from neo4j import GraphDatabase
import sys

def list_team_players(team: str):
    """팀의 선수 리스트 출력 (출전 시간순)"""

    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

    with driver.session() as session:
        result = session.run("""
            MATCH (p:Player {team: $team})
            WHERE p.avg_minutes IS NOT NULL
            RETURN p.name AS name,
                   p.position AS position,
                   p.avg_minutes AS minutes,
                   p.ppg AS ppg,
                   p.rpg AS rpg,
                   p.apg AS apg,
                   p.style_tags AS tags
            ORDER BY p.avg_minutes DESC
        """, team=team)

        players = list(result)

        if not players:
            print(f"❌ {team} 선수 없음 (PlayerBoxScore 데이터 없거나 팀 코드 오류)")
            driver.close()
            return

        print(f"=" * 80)
        print(f"{team} 선수 리스트 (25-26 시즌)")
        print(f"=" * 80)
        print()

        # 주전 (30분+)
        starters = [p for p in players if p['minutes'] >= 30]
        if starters:
            print(f"주전 (30분+): {len(starters)}명")
            print("-" * 80)
            for p in starters:
                tags = ', '.join(p['tags'][:2]) if p['tags'] else ''
                print(f"  {p['name']:30s} {p['position']:3s} {p['minutes']:4.1f}min {p['ppg']:4.1f}p {p['rpg']:4.1f}r {p['apg']:4.1f}a [{tags}]")
            print()

        # 로테이션 (20-30분)
        rotation = [p for p in players if 20 <= p['minutes'] < 30]
        if rotation:
            print(f"로테이션 (20-30분): {len(rotation)}명")
            print("-" * 80)
            for p in rotation:
                tags = ', '.join(p['tags'][:2]) if p['tags'] else ''
                print(f"  {p['name']:30s} {p['position']:3s} {p['minutes']:4.1f}min {p['ppg']:4.1f}p {p['rpg']:4.1f}r {p['apg']:4.1f}a [{tags}]")
            print()

        # 벤치 (20분 미만)
        bench = [p for p in players if p['minutes'] < 20]
        if bench:
            print(f"벤치 (<20분): {len(bench)}명")
            print("-" * 80)
            for p in bench[:10]:  # 상위 10명만
                tags = ', '.join(p['tags'][:2]) if p['tags'] else ''
                print(f"  {p['name']:30s} {p['position']:3s} {p['minutes']:4.1f}min {p['ppg']:4.1f}p {p['rpg']:4.1f}r {p['apg']:4.1f}a [{tags}]")
            if len(bench) > 10:
                print(f"  ... 외 {len(bench)-10}명")
            print()

        print("=" * 80)
        print(f"💡 Lineup 작성 시 위 이름을 정확히 복사하세요")
        print("=" * 80)

    driver.close()

def list_all_teams():
    """모든 팀 요약"""

    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

    with driver.session() as session:
        result = session.run("""
            MATCH (p:Player)
            WHERE p.team IS NOT NULL
            RETURN p.team AS team, count(*) AS player_count
            ORDER BY team
        """)

        teams = list(result)

        print("=" * 80)
        print("팀별 선수 수 (25-26 시즌)")
        print("=" * 80)
        print()

        for t in teams:
            print(f"  {t['team']:5s} - {t['player_count']:3d}명")

        print()
        print("=" * 80)
        print("💡 특정 팀 선수 리스트: python list_team_players.py <TEAM>")
        print("   예시: python list_team_players.py HOU")
        print("=" * 80)

    driver.close()

def main():
    if len(sys.argv) < 2:
        print("사용법: python list_team_players.py <TEAM>")
        print("        python list_team_players.py --all")
        print()
        print("예시:")
        print("  python list_team_players.py HOU")
        print("  python list_team_players.py OKC")
        print("  python list_team_players.py --all")
        sys.exit(1)

    team = sys.argv[1].upper()

    if team == "--ALL":
        list_all_teams()
    else:
        list_team_players(team)

if __name__ == "__main__":
    main()
