#!/usr/bin/env python3
"""
NBA Schedule Collector using ESPN API
Fetches NBA game schedules and stores them in SQLite
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import json

class NBACollector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

    def fetch_games(self, date: str = None) -> List[Dict]:
        """
        Fetch NBA games for a specific date
        date format: YYYYMMDD (e.g., 20260115)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        url = f"{self.base_url}?dates={date}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for event in data.get('events', []):
                game = self._parse_game(event, date)
                if game:
                    games.append(game)

            return games

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching NBA games for {date}: {e}")
            return []

    def fetch_month(self, year: int, month: int) -> List[Dict]:
        """Fetch all games for a specific month"""
        from calendar import monthrange

        all_games = []
        days_in_month = monthrange(year, month)[1]

        for day in range(1, days_in_month + 1):
            date = f"{year}{month:02d}{day:02d}"
            games = self.fetch_games(date)
            all_games.extend(games)
            print(f"  📅 {date}: {len(games)} games")

        return all_games

    def _parse_game(self, event: Dict, date: str) -> Dict:
        """Parse ESPN API game data"""
        try:
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])

            home_team = None
            away_team = None

            for comp in competitors:
                team_abbr = comp.get('team', {}).get('abbreviation', '')
                if comp.get('homeAway') == 'home':
                    home_team = team_abbr
                else:
                    away_team = team_abbr

            game_date = event.get('date', '')
            game_datetime = datetime.fromisoformat(game_date.replace('Z', '+00:00'))

            # 날짜와 시간 모두 KST 기준 (한국 시청자 기준)
            from zoneinfo import ZoneInfo
            kst = ZoneInfo('Asia/Seoul')
            game_kst = game_datetime.astimezone(kst)

            game_date_kst = game_kst.strftime('%Y-%m-%d')   # 한국 날짜
            game_time_kst = game_kst.strftime('%H:%M')      # 한국 시간

            game_id = event.get('id', '')

            # Determine importance based on team rankings
            importance = self._determine_importance(home_team, away_team, event)

            return {
                'id': game_id,
                'date': game_date_kst,
                'time': game_time_kst,
                'home_team': home_team,
                'away_team': away_team,
                'importance': importance,
                'status': 'pending',
                'season': '2025-26',
                'notes': ''
            }

        except Exception as e:
            print(f"⚠️  Error parsing game: {e}")
            return None

    def _determine_importance(self, home: str, away: str, event: Dict) -> str:
        """
        Determine game importance
        HIGH: Playoff contenders, rivals, marquee matchups
        MID: Regular games
        LOW: Tanking teams
        """
        # Top teams (simplified - can be enhanced with standings API)
        top_teams = ['BOS', 'LAL', 'GSW', 'MIL', 'PHX', 'DEN', 'MIA', 'PHI', 'LAC']

        if home in top_teams and away in top_teams:
            return 'HIGH'
        elif home in top_teams or away in top_teams:
            return 'MID'
        else:
            return 'LOW'

    def save_to_db(self, games: List[Dict]):
        """Save games to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for game in games:
            cursor.execute("""
                INSERT OR REPLACE INTO nba_games
                (id, date, time, home_team, away_team, importance, status, season, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game['id'],
                game['date'],
                game['time'],
                game['home_team'],
                game['away_team'],
                game['importance'],
                game['status'],
                game['season'],
                game['notes']
            ))

        conn.commit()
        conn.close()

        print(f"✅ Saved {len(games)} NBA games to database")

    def collect_and_save(self, date: str = None):
        """Main method: collect and save games"""
        if date:
            print(f"🏀 Fetching NBA games for {date}...")
            games = self.fetch_games(date)
        else:
            print(f"🏀 Fetching NBA games for today...")
            games = self.fetch_games()

        if games:
            self.save_to_db(games)

        return games

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH', '/Users/js/g9/scheduler/data/schedules.db')
    collector = NBACollector(db_path)

    if len(sys.argv) > 1:
        # Collect specific date: YYYYMMDD
        date = sys.argv[1]
        games = collector.collect_and_save(date)
    else:
        # Collect today
        games = collector.collect_and_save()

    print(f"\n📊 Summary: {len(games)} games collected")
    for game in games[:5]:  # Show first 5
        print(f"  {game['date']} {game['time']} - {game['away_team']} @ {game['home_team']} [{game['importance']}]")
