#!/usr/bin/env python3
"""
NBA Season Backfill - Load entire season schedule
"""
import os
import sys
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class NBASeasonBackfill:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.espn_base = os.getenv('ESPN_API_BASE', 'https://site.api.espn.com/apis/site/v2/sports')
        
    def fetch_season_schedule(self, season: str = "2025"):
        """Fetch entire NBA season schedule"""
        # ESPN API for NBA schedule
        url = f"{self.espn_base}/basketball/nba/scoreboard"
        
        games = []
        # Fetch from Oct 2024 to Jun 2025 (full season)
        dates = self._generate_season_dates(season)
        
        print(f"📅 Fetching NBA {season} season schedule...")
        for date in dates:
            params = {'dates': date.replace('-', '')}
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                for event in data.get('events', []):
                    game = self._parse_game(event, date)
                    if game:
                        games.append(game)
                        
            except Exception as e:
                print(f"  Error fetching {date}: {e}")
                
            if len(games) % 50 == 0:
                print(f"  Fetched {len(games)} games...")
                
        return games
    
    def _generate_season_dates(self, season: str):
        """Generate all dates for NBA season"""
        from datetime import timedelta
        
        # NBA season: Oct 2024 - Jun 2025
        start = datetime(2024, 10, 1)
        end = datetime(2025, 6, 30)
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
            
        return dates
    
    def _parse_game(self, event: dict, date: str) -> dict:
        """Parse ESPN event to game dict"""
        try:
            game_id = event['id']
            name = event['name']
            away_team, home_team = name.split(' at ')
            
            # Get game time
            game_date = event.get('date', '')
            if game_date:
                dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                # Convert to KST (UTC+9)
                from datetime import timezone, timedelta
                kst = timezone(timedelta(hours=9))
                dt_kst = dt.astimezone(kst)
                time_str = dt_kst.strftime('%H:%M')
                date_str = dt_kst.strftime('%Y-%m-%d')
            else:
                time_str = "TBD"
                date_str = date
                
            return {
                'id': f"nba_{game_id}",
                'date': date_str,
                'time': time_str,
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'importance': 'MID',
                'notes': ''
            }
        except Exception as e:
            return None
    
    def save_to_db(self, games: list):
        """Save games to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for game in games:
            cursor.execute("""
                INSERT OR REPLACE INTO nba_games
                (id, date, time, home_team, away_team, importance, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                game['id'], game['date'], game['time'],
                game['home_team'], game['away_team'],
                game['importance'], game['notes']
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Saved {len(games)} NBA games to database")

if __name__ == '__main__':
    db_path = os.getenv('DB_PATH', '/Users/js/g9/scheduler/data/schedules.db')
    
    backfill = NBASeasonBackfill(db_path)
    games = backfill.fetch_season_schedule("2025")
    
    print(f"\n📊 Total games fetched: {len(games)}")
    
    if games:
        backfill.save_to_db(games)
        print("✅ Backfill complete!")
