#!/usr/bin/env python3
"""
내일 NBA 경기 스케줄 가져오기
ESPN API에서 내일 날짜의 경기 목록을 조회
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

def get_tomorrow_date() -> str:
    """내일 날짜를 YYYYMMDD 형식으로 반환"""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%Y%m%d")

def fetch_schedule(date: str) -> Optional[Dict]:
    """ESPN API에서 특정 날짜의 스케줄 가져오기"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return None

def parse_games(data: Dict) -> List[Dict]:
    """경기 데이터 파싱"""
    if not data or 'events' not in data:
        return []

    games = []
    for event in data['events']:
        try:
            game_id = event['id']

            # 경기 정보
            competition = event['competitions'][0]

            # 팀 정보
            home_team = None
            away_team = None
            for team in competition['competitors']:
                team_info = {
                    'abbr': team['team']['abbreviation'],
                    'name': team['team']['displayName'],
                    'record': team.get('records', [{}])[0].get('summary', 'N/A')
                }

                if team['homeAway'] == 'home':
                    home_team = team_info
                else:
                    away_team = team_info

            # 경기 시간
            game_time = event.get('date', '')
            game_dt = datetime.strptime(game_time, "%Y-%m-%dT%H:%MZ") if game_time else None

            # 경기장
            venue = competition.get('venue', {})

            games.append({
                'game_id': game_id,
                'date': game_time[:10] if game_time else '',
                'time': game_dt.strftime("%H:%M") if game_dt else 'TBD',
                'home_team': home_team,
                'away_team': away_team,
                'venue': {
                    'name': venue.get('fullName', 'TBD'),
                    'city': venue.get('address', {}).get('city', 'TBD')
                },
                'status': competition.get('status', {}).get('type', {}).get('description', 'Scheduled')
            })
        except Exception as e:
            print(f"⚠️  경기 파싱 실패 ({event.get('id', 'unknown')}): {e}")
            continue

    return games

def display_games(games: List[Dict]):
    """경기 목록 출력"""
    if not games:
        print("\n❌ 내일 예정된 경기가 없습니다.")
        return

    print(f"\n{'='*70}")
    print(f"📅 내일 NBA 경기 스케줄 ({len(games)}경기)")
    print(f"{'='*70}\n")

    for i, game in enumerate(games, 1):
        home = game['home_team']
        away = game['away_team']

        print(f"{i}. {game['time']} - {game['status']}")
        print(f"   {away['abbr']} @ {home['abbr']}")
        print(f"   {away['name']} ({away['record']})")
        print(f"   vs")
        print(f"   {home['name']} ({home['record']})")
        print(f"   📍 {game['venue']['name']}, {game['venue']['city']}")
        print(f"   🆔 Game ID: {game['game_id']}")
        print()

def save_schedule(games: List[Dict], filename: str = "tomorrow_games.json"):
    """스케줄을 JSON 파일로 저장"""
    filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"✅ 스케줄 저장: {filepath}")

def main():
    """메인 함수"""
    print("="*70)
    print("ESPN API에서 내일 경기 스케줄 가져오기")
    print("="*70)

    # 내일 날짜
    tomorrow = get_tomorrow_date()
    tomorrow_readable = datetime.strptime(tomorrow, "%Y%m%d").strftime("%Y년 %m월 %d일")
    print(f"\n📅 조회 날짜: {tomorrow_readable} ({tomorrow})")

    # API 호출
    print("🔄 ESPN API 호출 중...")
    data = fetch_schedule(tomorrow)

    if not data:
        print("❌ 데이터를 가져올 수 없습니다.")
        return

    # 파싱
    games = parse_games(data)

    # 출력
    display_games(games)

    # 저장
    if games:
        save_schedule(games)
        print(f"\n✅ 총 {len(games)}개 경기 정보 저장 완료")

    return games

if __name__ == "__main__":
    main()
