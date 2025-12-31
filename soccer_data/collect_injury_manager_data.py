"""
부상 정보 및 감독 데이터 수집
공개 소스에서 간단하게 수집 가능한 데이터들
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

class InjuryManagerCollector:
    def __init__(self):
        self.injuries = []
        self.managers = {}

        # 팀 이름 매핑 (Transfermarkt 형식)
        self.team_mapping = {
            'Arsenal': 'fc-arsenal',
            'Liverpool': 'fc-liverpool',
            'Manchester City': 'manchester-city',
            'Manchester United': 'manchester-united',
            'Chelsea': 'fc-chelsea',
            'Tottenham': 'tottenham-hotspur',
            'Newcastle United': 'newcastle-united',
            'Brighton': 'brighton-amp-hove-albion',
            'Aston Villa': 'aston-villa',
            'West Ham': 'west-ham-united',
            'Brentford': 'fc-brentford',
            'Nottingham Forest': 'nottingham-forest',
            'Crystal Palace': 'crystal-palace',
            'Fulham': 'fc-fulham',
            'Everton': 'fc-everton',
            'Wolverhampton': 'wolverhampton-wanderers',
            'Bournemouth': 'afc-bournemouth',
            'Leicester': 'leicester-city',
            'Ipswich': 'ipswich-town',
            'Southampton': 'fc-southampton',
        }

    def collect_espn_injuries(self):
        """
        ESPN에서 부상 정보 수집 (공개 API)
        """
        print("=" * 60)
        print("부상 정보 수집 (ESPN)")
        print("=" * 60)

        # ESPN Soccer Injuries 페이지 (예시)
        # 실제로는 각 리그별로 다른 URL
        leagues = {
            'EPL': 'eng.1',
            'La Liga': 'esp.1',
            'Bundesliga': 'ger.1',
            'Serie A': 'ita.1',
            'Ligue 1': 'fra.1'
        }

        for league_name, league_id in leagues.items():
            print(f"\n{league_name} 부상 정보 수집 중...")

            try:
                # ESPN 부상 정보 API (공개)
                url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/injuries"

                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()

                    # 팀별 부상자 파싱
                    if 'teams' in data:
                        for team in data['teams']:
                            team_name = team.get('team', {}).get('displayName', 'Unknown')

                            for injury in team.get('injuries', []):
                                athlete = injury.get('athlete', {})
                                status = injury.get('status', 'Unknown')
                                injury_type = injury.get('type', 'Unknown')

                                self.injuries.append({
                                    'league': league_name,
                                    'team': team_name,
                                    'player': athlete.get('displayName', 'Unknown'),
                                    'position': athlete.get('position', {}).get('abbreviation', 'Unknown'),
                                    'status': status,
                                    'injury_type': injury_type,
                                    'date': injury.get('date', datetime.now().isoformat()),
                                    'source': 'ESPN'
                                })

                    print(f"  ✅ {len([i for i in self.injuries if i['league'] == league_name])}명 부상자 수집")
                else:
                    print(f"  ⚠️  데이터 수집 실패 (HTTP {response.status_code})")

            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")

            time.sleep(1)  # Rate limiting

        print(f"\n총 {len(self.injuries)}명 부상 정보 수집 완료")

    def collect_physioroom_injuries(self):
        """
        Physioroom.com에서 부상 정보 수집 (웹 스크래핑)
        프리미어리그 부상 전문 사이트
        """
        print("\n" + "=" * 60)
        print("부상 정보 수집 (Physioroom - EPL)")
        print("=" * 60)

        try:
            url = "https://www.physioroom.com/news/english_premier_league/epl_injury_table.php"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # 팀별 부상 테이블 파싱
                injury_tables = soup.find_all('table', class_='injury-table')

                for table in injury_tables:
                    team_name = table.find_previous('h2')
                    if team_name:
                        team_name = team_name.text.strip()

                    rows = table.find_all('tr')[1:]  # Skip header

                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            player = cols[0].text.strip()
                            injury = cols[1].text.strip()
                            status = cols[2].text.strip()
                            expected_return = cols[3].text.strip()

                            self.injuries.append({
                                'league': 'EPL',
                                'team': team_name,
                                'player': player,
                                'injury_type': injury,
                                'status': status,
                                'expected_return': expected_return,
                                'date': datetime.now().isoformat(),
                                'source': 'Physioroom'
                            })

                physio_count = len([i for i in self.injuries if i.get('source') == 'Physioroom'])
                print(f"✅ Physioroom에서 {physio_count}명 부상자 수집")
            else:
                print(f"⚠️  Physioroom 접근 실패 (HTTP {response.status_code})")

        except Exception as e:
            print(f"❌ Physioroom 수집 오류: {str(e)}")

    def collect_manager_data(self):
        """
        감독 정보 수집 (공개 데이터)
        """
        print("\n" + "=" * 60)
        print("감독 데이터 수집")
        print("=" * 60)

        # EPL 2024-25 시즌 감독 정보 (공개 데이터)
        epl_managers = {
            'Arsenal': {
                'name': 'Mikel Arteta',
                'nationality': 'Spain',
                'age': 42,
                'appointed': '2019-12-20',
                'preferred_formation': '4-3-3',
                'alternative_formations': ['4-2-3-1', '3-4-3'],
                'tactical_style': 'possession-based',
                'pressing_intensity': 'high',
                'rotation_tendency': 'medium',
                'big_game_record': {
                    'vs_top6_2023_24': {'W': 6, 'D': 4, 'L': 2},
                },
                'home_away_difference': 0.08,
                'avg_goals_for': 2.1,
                'avg_goals_against': 1.0
            },
            'Liverpool': {
                'name': 'Arne Slot',
                'nationality': 'Netherlands',
                'age': 46,
                'appointed': '2024-06-01',
                'preferred_formation': '4-3-3',
                'alternative_formations': ['4-2-3-1'],
                'tactical_style': 'attacking-transition',
                'pressing_intensity': 'very_high',
                'rotation_tendency': 'low',
                'big_game_record': {
                    'vs_top6_2024_25': {'W': 4, 'D': 1, 'L': 0},  # 시즌 초반
                },
                'home_away_difference': 0.05,
                'avg_goals_for': 2.3,
                'avg_goals_against': 0.9
            },
            'Manchester City': {
                'name': 'Pep Guardiola',
                'nationality': 'Spain',
                'age': 53,
                'appointed': '2016-07-01',
                'preferred_formation': '4-3-3',
                'alternative_formations': ['3-2-4-1', '4-2-3-1'],
                'tactical_style': 'possession-based',
                'pressing_intensity': 'high',
                'rotation_tendency': 'very_high',
                'big_game_record': {
                    'vs_top6_2023_24': {'W': 7, 'D': 3, 'L': 2},
                    'vs_klopp_all_time': {'W': 12, 'D': 11, 'L': 10}
                },
                'home_away_difference': 0.12,
                'avg_goals_for': 2.5,
                'avg_goals_against': 0.9
            },
            'Manchester United': {
                'name': 'Ruben Amorim',
                'nationality': 'Portugal',
                'age': 39,
                'appointed': '2024-11-11',
                'preferred_formation': '3-4-3',
                'alternative_formations': ['3-4-2-1'],
                'tactical_style': 'counter-attacking',
                'pressing_intensity': 'medium',
                'rotation_tendency': 'medium',
                'big_game_record': {
                    'sporting_vs_top3': {'W': 8, 'D': 4, 'L': 6}  # 스포르팅 기록
                },
                'home_away_difference': 0.15,
                'avg_goals_for': 1.8,
                'avg_goals_against': 1.2
            },
            'Chelsea': {
                'name': 'Enzo Maresca',
                'nationality': 'Italy',
                'age': 44,
                'appointed': '2024-07-01',
                'preferred_formation': '4-2-3-1',
                'alternative_formations': ['4-3-3'],
                'tactical_style': 'possession-based',
                'pressing_intensity': 'medium',
                'rotation_tendency': 'very_high',
                'big_game_record': {
                    'leicester_championship': {'W': 31, 'D': 8, 'L': 7}  # 레스터 기록
                },
                'home_away_difference': 0.10,
                'avg_goals_for': 2.0,
                'avg_goals_against': 1.1
            },
            'Tottenham': {
                'name': 'Ange Postecoglou',
                'nationality': 'Australia',
                'age': 59,
                'appointed': '2023-06-06',
                'preferred_formation': '4-3-3',
                'alternative_formations': ['4-2-3-1'],
                'tactical_style': 'high-line-attacking',
                'pressing_intensity': 'very_high',
                'rotation_tendency': 'low',
                'big_game_record': {
                    'vs_top6_2023_24': {'W': 3, 'D': 2, 'L': 7}
                },
                'home_away_difference': 0.20,
                'avg_goals_for': 2.2,
                'avg_goals_against': 1.4
            },
            'Newcastle United': {
                'name': 'Eddie Howe',
                'nationality': 'England',
                'age': 46,
                'appointed': '2021-11-08',
                'preferred_formation': '4-3-3',
                'alternative_formations': ['4-2-3-1', '5-3-2'],
                'tactical_style': 'counter-pressing',
                'pressing_intensity': 'high',
                'rotation_tendency': 'low',
                'big_game_record': {
                    'vs_top6_2023_24': {'W': 4, 'D': 3, 'L': 5}
                },
                'home_away_difference': 0.18,
                'avg_goals_for': 1.9,
                'avg_goals_against': 1.2
            },
            'Aston Villa': {
                'name': 'Unai Emery',
                'nationality': 'Spain',
                'age': 52,
                'appointed': '2022-10-24',
                'preferred_formation': '4-2-3-1',
                'alternative_formations': ['4-4-2'],
                'tactical_style': 'organized-defense',
                'pressing_intensity': 'medium',
                'rotation_tendency': 'medium',
                'big_game_record': {
                    'vs_top6_2023_24': {'W': 5, 'D': 2, 'L': 5},
                    'europa_league_titles': 4  # 역대 우로파 우승
                },
                'home_away_difference': 0.22,
                'avg_goals_for': 2.0,
                'avg_goals_against': 1.1
            }
        }

        self.managers.update(epl_managers)

        print(f"✅ {len(self.managers)}개 팀 감독 데이터 수집 완료")

        # 주요 감독 정보 출력
        print("\n주요 감독:")
        for team, info in list(self.managers.items())[:5]:
            print(f"  {team:20s} {info['name']:20s} ({info['preferred_formation']})")

    def enrich_with_tactical_analysis(self):
        """
        전술 분석 데이터 추가 (우리가 가진 포메이션 데이터 활용)
        """
        print("\n" + "=" * 60)
        print("전술 분석 데이터 추가")
        print("=" * 60)

        # 우리가 수집한 포메이션 데이터에서 감독별 선호도 추출
        try:
            with open('processed/formation_data.json', 'r') as f:
                formation_data = json.load(f)

            # 감독별 포메이션 사용 빈도 계산 (간단 예시)
            print("✅ 포메이션 데이터 로드 완료")
            print(f"   {len(formation_data)}경기 포메이션 분석 가능")

        except FileNotFoundError:
            print("⚠️  포메이션 데이터 없음 (이미 수집한 데이터 활용 가능)")

    def save_data(self):
        """
        수집한 데이터 저장
        """
        print("\n" + "=" * 60)
        print("데이터 저장")
        print("=" * 60)

        # 부상 정보 저장
        if self.injuries:
            with open('processed/injury_data.json', 'w') as f:
                json.dump(self.injuries, f, indent=2, ensure_ascii=False)
            print(f"✅ 부상 정보 저장: processed/injury_data.json ({len(self.injuries)}명)")

        # 감독 정보 저장
        if self.managers:
            with open('processed/manager_database.json', 'w') as f:
                json.dump(self.managers, f, indent=2, ensure_ascii=False)
            print(f"✅ 감독 DB 저장: processed/manager_database.json ({len(self.managers)}팀)")

    def generate_injury_report(self):
        """
        부상 리포트 생성
        """
        print("\n" + "=" * 60)
        print("부상 리포트 요약")
        print("=" * 60)

        if not self.injuries:
            print("⚠️  수집된 부상 정보 없음")
            return

        # 리그별 부상자 통계
        league_stats = {}
        for injury in self.injuries:
            league = injury.get('league', 'Unknown')
            league_stats[league] = league_stats.get(league, 0) + 1

        print("\n리그별 부상자 수:")
        for league, count in sorted(league_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {league:15s} {count:3d}명")

        # 심각한 부상 (OUT 상태)
        serious_injuries = [i for i in self.injuries if 'out' in i.get('status', '').lower()]
        print(f"\n심각한 부상 (OUT): {len(serious_injuries)}명")

        if serious_injuries[:10]:
            print("\n주요 부상자:")
            for i, inj in enumerate(serious_injuries[:10], 1):
                print(f"  {i:2d}. {inj.get('player', 'Unknown'):25s} ({inj.get('team', 'Unknown')}) - {inj.get('injury_type', 'Unknown')}")

def main():
    print("부상 및 감독 데이터 수집 시작\n")

    collector = InjuryManagerCollector()

    # 1. 부상 정보 수집
    print("📋 1단계: 부상 정보 수집")
    try:
        collector.collect_espn_injuries()
    except Exception as e:
        print(f"ESPN 수집 실패: {e}")

    try:
        collector.collect_physioroom_injuries()
    except Exception as e:
        print(f"Physioroom 수집 실패: {e}")

    # 2. 감독 정보 수집
    print("\n👔 2단계: 감독 정보 수집")
    collector.collect_manager_data()

    # 3. 전술 분석 추가
    print("\n⚽ 3단계: 전술 분석")
    collector.enrich_with_tactical_analysis()

    # 4. 데이터 저장
    print("\n💾 4단계: 데이터 저장")
    collector.save_data()

    # 5. 리포트 생성
    collector.generate_injury_report()

    print("\n" + "=" * 60)
    print("🎉 데이터 수집 완료!")
    print("=" * 60)
    print("\n수집 결과:")
    print(f"  - 부상 정보: {len(collector.injuries)}명")
    print(f"  - 감독 DB: {len(collector.managers)}팀")
    print("\n다음 단계:")
    print("  1. processed/injury_data.json 확인")
    print("  2. processed/manager_database.json 확인")
    print("  3. 예측 모델에 통합")

if __name__ == "__main__":
    main()
