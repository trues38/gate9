
import requests
import json
import os

# Config
OUTPUT_FILE = "/Users/js/g9/nba_data/schedule_2025.json"

# NBA API Endpoint for Schedule
# We typically use the CDN for full season data
SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

def fetch_schedule():
    print(f"Fetching 2025-26 Schedule from {SCHEDULE_URL}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.nba.com/"
        }
        
        response = requests.get(SCHEDULE_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # The structure is typically data['leagueSchedule']['gameDates']
        # We want to flatten this for DuckDB
        
        games = []
        if 'leagueSchedule' in data and 'gameDates' in data['leagueSchedule']:
            for date_entry in data['leagueSchedule']['gameDates']:
                game_date = date_entry['gameDate'] # "10/22/2024 00:00:00" or similar
                
                for game in date_entry['games']:
                    games.append({
                        "game_id": game['gameId'],
                        "date": game_date,
                        "home_team": game['homeTeam']['teamTricode'],
                        "away_team": game['awayTeam']['teamTricode'],
                        "home_id": game['homeTeam']['teamId'],
                        "away_id": game['awayTeam']['teamId'],
                        "arena": game['arenaName'],
                        "city": game['arenaCity']
                        # Add valid time logic if needed
                    })
        
        print(f"Parsed {len(games)} games from schedule.")
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(games, f, indent=2)
            
        print(f"Successfully saved schedule to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error fetching schedule: {e}")

if __name__ == "__main__":
    fetch_schedule()
