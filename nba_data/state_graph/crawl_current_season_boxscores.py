#!/usr/bin/env python3
"""
25-26 시즌 선수 box score 크롤링
2025-10-01 ~ 현재까지

ESPN Box Score API:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}
"""

import requests
import json
from datetime import datetime, timedelta
import time
from pathlib import Path

class BoxScoreCrawler:
    def __init__(self, output_dir="player_boxscores_2025_26"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        self.summary_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"

    def get_games_for_date(self, date_str: str):
        """특정 날짜의 경기 목록 가져오기"""
        url = f"{self.base_url}?dates={date_str}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            if 'events' in data:
                for event in data['events']:
                    # 완료된 경기만
                    if event['status']['type'].get('completed', False):
                        games.append({
                            'game_id': event['id'],
                            'date': event['date'][:10],
                            'name': event['name'],
                            'status': event['status']['type']['description']
                        })

            return games
        except Exception as e:
            print(f"Error fetching games for {date_str}: {e}")
            return []

    def get_boxscore(self, game_id: str):
        """특정 경기의 box score 가져오기"""
        url = f"{self.summary_url}?event={game_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'boxscore' not in data or 'players' not in data['boxscore']:
                return None

            boxscore_data = {
                'game_id': game_id,
                'teams': []
            }

            # 양 팀 선수 스탯 파싱
            for team_data in data['boxscore']['players']:
                team_info = {
                    'team': team_data['team']['abbreviation'],
                    'team_name': team_data['team']['displayName'],
                    'players': []
                }

                # 통계 카테고리 (보통 1개, 전체 스탯)
                if team_data.get('statistics'):
                    stats_cat = team_data['statistics'][0]
                    labels = stats_cat.get('labels', [])

                    # 각 선수 파싱
                    for athlete_data in stats_cat.get('athletes', []):
                        athlete = athlete_data['athlete']
                        stats = athlete_data['stats']

                        player = {
                            'player_id': athlete['id'],
                            'name': athlete['displayName'],
                            'position': athlete.get('position', {}).get('abbreviation', 'N/A'),
                            'stats': {}
                        }

                        # 스탯을 라벨과 매칭
                        for i, label in enumerate(labels):
                            if i < len(stats):
                                player['stats'][label] = stats[i]

                        team_info['players'].append(player)

                boxscore_data['teams'].append(team_info)

            return boxscore_data

        except Exception as e:
            print(f"Error fetching boxscore for {game_id}: {e}")
            return None

    def crawl_date_range(self, start_date: str, end_date: str):
        """날짜 범위의 모든 box score 크롤링"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        total_games = 0
        total_boxscores = 0

        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            print(f"\n{'='*80}")
            print(f"📅 {current.strftime('%Y-%m-%d')} 크롤링 중...")
            print(f"{'='*80}")

            # 해당 날짜의 경기 가져오기
            games = self.get_games_for_date(date_str)
            print(f"찾은 경기: {len(games)}개")

            date_boxscores = []

            for game in games:
                total_games += 1
                print(f"  {game['name']} (ID: {game['game_id']}) ... ", end='')

                # Box score 가져오기
                boxscore = self.get_boxscore(game['game_id'])

                if boxscore:
                    boxscore['date'] = game['date']
                    boxscore['game_name'] = game['name']
                    date_boxscores.append(boxscore)
                    total_boxscores += 1

                    # 선수 수 확인
                    total_players = sum(len(team['players']) for team in boxscore['teams'])
                    print(f"✅ ({total_players}명)")
                else:
                    print("❌ (box score 없음)")

                # Rate limiting
                time.sleep(0.5)

            # 날짜별로 파일 저장
            if date_boxscores:
                output_file = self.output_dir / f"boxscores_{date_str}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(date_boxscores, f, indent=2, ensure_ascii=False)
                print(f"\n💾 저장: {output_file} ({len(date_boxscores)}개 경기)")

            current += timedelta(days=1)

        print(f"\n{'='*80}")
        print(f"✅ 크롤링 완료!")
        print(f"{'='*80}")
        print(f"총 경기: {total_games}개")
        print(f"Box score 수집: {total_boxscores}개")
        print(f"저장 위치: {self.output_dir}/")
        print()

def main():
    import argparse

    parser = argparse.ArgumentParser(description='25-26 시즌 Box Score 크롤러')
    parser.add_argument('--start-date', default='2025-10-01', help='시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end-date', default=datetime.now().strftime('%Y-%m-%d'), help='종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--output-dir', default='player_boxscores_2025_26', help='출력 디렉토리')

    args = parser.parse_args()

    print("=" * 80)
    print("25-26 시즌 선수 Box Score 크롤러")
    print("=" * 80)
    print(f"시작 날짜: {args.start_date}")
    print(f"종료 날짜: {args.end_date}")
    print(f"출력 위치: {args.output_dir}/")
    print()

    crawler = BoxScoreCrawler(output_dir=args.output_dir)
    crawler.crawl_date_range(args.start_date, args.end_date)

if __name__ == "__main__":
    main()
