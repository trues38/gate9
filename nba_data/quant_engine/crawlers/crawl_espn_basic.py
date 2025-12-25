import requests
import json
import os
import argparse
from datetime import datetime, timedelta

# Configuration
RAW_GAMES_DIR = "raw/games"
RAW_BOXSCORE_DIR = "raw/boxscore"
os.makedirs(RAW_GAMES_DIR, exist_ok=True)
os.makedirs(RAW_BOXSCORE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def fetch_schedule(date_str):
    """
    Fetches NBA schedule for a specific date (YYYYMMDD).
    URL: https://site.web.api.espn.com/apis/v2/sports/basketball/nba/scoreboard?dates={date_str}
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    print(f"📅 Fetching Schedule: {date_str}...")
    
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        
        # Save Raw
        filepath = os.path.join(RAW_GAMES_DIR, f"{date_str}_games.json")
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Saved schedule to {filepath}")
        
        return data
    except Exception as e:
        print(f"❌ Error fetching schedule for {date_str}: {e}")
        return None

def fetch_boxscore(game_id):
    """
    Fetches NBA boxscore/summary for a specific game ID.
    URL: https://site.web.api.espn.com/apis/v2/sports/basketball/nba/summary?event={game_id}
    """
    filepath = os.path.join(RAW_BOXSCORE_DIR, f"{game_id}.json")
    if os.path.exists(filepath):
        print(f"⏭️  Boxscore {game_id} already exists. Skipping.")
        return

    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    print(f"📊 Fetching Boxscore: {game_id}...")
    
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Saved boxscore to {filepath}")
        
    except Exception as e:
        print(f"❌ Error fetching boxscore {game_id}: {e}")

def process_date(date_str):
    """
    Orchestrator: Fetch Schedule -> Extract Game IDs -> Fetch Boxscores
    """
    schedule = fetch_schedule(date_str)
    if not schedule:
        return

    events = schedule.get("events", [])
    print(f"Found {len(events)} games for {date_str}.")
    
    for event in events:
        game_id = event.get("id")
        status = event.get("status", {}).get("type", {}).get("state")
        
        # specific logic: Only fetch boxscores for completed (post) or live games? 
        # Usually we want everything, but mainly completed for stats.
        # State: 'post' = finished. 'in' = live. 'pre' = scheduled.
        
        print(f"   > Game {game_id}: {event.get('name')} ({status})")
        
        fetch_boxscore(game_id)

def main():
    parser = argparse.ArgumentParser(description="ESPN Raw Data Crawler")
    parser.add_argument("--date", type=str, help="YYYYMMDD", required=True)
    parser.add_argument("--days", type=int, default=1, help="Number of days to crawl")
    
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.date, "%Y%m%d")
    
    for i in range(args.days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y%m%d")
        process_date(date_str)

if __name__ == "__main__":
    main()
