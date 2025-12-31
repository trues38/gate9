#!/usr/bin/env python3
"""
Soccer Schedule Collector using football-data.org API
Fetches top 5 European leagues schedules
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import json

class SoccerCollector:
    def __init__(self, db_path: str, api_key: str):
        self.db_path = db_path
        self.api_key = api_key
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {
            'X-Auth-Token': self.api_key
        }

        # League IDs
        self.leagues = {
            'PL': 2021,    # Premier League
            'PD': 2014,    # La Liga
            'SA': 2019,    # Serie A
            'BL1': 2002,   # Bundesliga
            'FL1': 2015    # Ligue 1
        }

        self.league_names = {
            2021: 'EPL',
            2014: 'LaLiga',
            2019: 'SerieA',
            2002: 'Bundesliga',
            2015: 'Ligue1'
        }

    def fetch_league_matches(self, league_code: str, date_from: str = None, date_to: str = None) -> List[Dict]:
        """
        Fetch matches for a specific league
        date format: YYYY-MM-DD
        """
        league_id = self.leagues.get(league_code)
        if not league_id:
            print(f"❌ Unknown league code: {league_code}")
            return []

        url = f"{self.base_url}/competitions/{league_id}/matches"

        params = {}
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            matches = []
            for match in data.get('matches', []):
                parsed = self._parse_match(match, league_id)
                if parsed:
                    matches.append(parsed)

            return matches

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {league_code} matches: {e}")
            return []

    def fetch_all_leagues(self, date_from: str = None, date_to: str = None) -> List[Dict]:
        """Fetch matches from all top 5 leagues"""
        all_matches = []

        for league_code in self.leagues.keys():
            print(f"  ⚽ Fetching {league_code}...")
            matches = self.fetch_league_matches(league_code, date_from, date_to)
            all_matches.extend(matches)
            print(f"    Found {len(matches)} matches")

        return all_matches

    def fetch_month(self, year: int, month: int) -> List[Dict]:
        """Fetch all matches for a specific month"""
        from calendar import monthrange

        date_from = f"{year}-{month:02d}-01"
        days_in_month = monthrange(year, month)[1]
        date_to = f"{year}-{month:02d}-{days_in_month}"

        print(f"⚽ Fetching soccer matches from {date_from} to {date_to}")
        return self.fetch_all_leagues(date_from, date_to)

    def _parse_match(self, match: Dict, league_id: int) -> Dict:
        """Parse football-data.org match data"""
        try:
            match_id = str(match.get('id', ''))
            utc_date = match.get('utcDate', '')

            if not utc_date:
                return None

            # Parse datetime
            match_datetime = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))

            # Convert to KST
            from zoneinfo import ZoneInfo
            kst = ZoneInfo('Asia/Seoul')
            match_kst = match_datetime.astimezone(kst)

            home_team = match.get('homeTeam', {}).get('shortName', '')
            away_team = match.get('awayTeam', {}).get('shortName', '')

            # Determine importance
            importance = self._determine_importance(home_team, away_team, league_id)

            league_name = self.league_names.get(league_id, 'Unknown')

            return {
                'id': f"soccer_{league_name}_{match_id}",
                'date': match_kst.strftime('%Y-%m-%d'),
                'time': match_kst.strftime('%H:%M'),
                'league': league_name,
                'home_team': home_team,
                'away_team': away_team,
                'importance': importance,
                'status': 'pending',
                'notes': ''
            }

        except Exception as e:
            print(f"⚠️  Error parsing match: {e}")
            return None

    def _determine_importance(self, home: str, away: str, league_id: int) -> str:
        """
        Determine match importance based on teams
        HIGH: Big 6 in EPL, El Clasico, Derby matches, etc.
        """
        # Top teams by league (simplified)
        top_teams = {
            2021: ['Manchester City', 'Arsenal', 'Liverpool', 'Chelsea', 'Man United', 'Tottenham'],
            2014: ['Real Madrid', 'Barcelona', 'Atlético', 'Athletic Club'],
            2019: ['Inter', 'Napoli', 'AC Milan', 'Juventus'],
            2002: ['Bayern', 'Dortmund', 'RB Leipzig', 'Leverkusen'],
            2015: ['PSG', 'Monaco', 'Marseille', 'Lyon']
        }

        league_tops = top_teams.get(league_id, [])

        # Check if both teams are top teams
        home_is_top = any(team in home for team in league_tops)
        away_is_top = any(team in away for team in league_tops)

        if home_is_top and away_is_top:
            return 'HIGH'
        elif home_is_top or away_is_top:
            return 'MID'
        else:
            return 'LOW'

    def save_to_db(self, matches: List[Dict]):
        """Save matches to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for match in matches:
            cursor.execute("""
                INSERT OR REPLACE INTO soccer_games
                (id, date, time, league, home_team, away_team, importance, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match['id'],
                match['date'],
                match['time'],
                match['league'],
                match['home_team'],
                match['away_team'],
                match['importance'],
                match['status'],
                match['notes']
            ))

        conn.commit()
        conn.close()

        print(f"✅ Saved {len(matches)} soccer matches to database")

    def collect_and_save(self, date_from: str = None, date_to: str = None):
        """Main method: collect and save matches"""
        print(f"⚽ Fetching soccer matches...")
        matches = self.fetch_all_leagues(date_from, date_to)

        if matches:
            self.save_to_db(matches)

        return matches

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH', '/Users/js/g9/scheduler/data/schedules.db')
    api_key = os.getenv('FOOTBALL_API_KEY')

    if not api_key:
        print("❌ FOOTBALL_API_KEY not found in .env")
        sys.exit(1)

    collector = SoccerCollector(db_path, api_key)

    if len(sys.argv) > 2:
        # Specific date range: YYYY-MM-DD YYYY-MM-DD
        date_from = sys.argv[1]
        date_to = sys.argv[2]
        matches = collector.collect_and_save(date_from, date_to)
    else:
        # Next 7 days
        today = datetime.now()
        date_from = today.strftime('%Y-%m-%d')
        date_to = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        matches = collector.collect_and_save(date_from, date_to)

    print(f"\n📊 Summary: {len(matches)} matches collected")
    for match in matches[:5]:  # Show first 5
        print(f"  {match['date']} {match['time']} [{match['league']}] {match['home_team']} vs {match['away_team']} [{match['importance']}]")
