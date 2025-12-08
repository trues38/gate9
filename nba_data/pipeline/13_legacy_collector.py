import requests
import json
import os
import time
from datetime import datetime, timedelta

# Constants
LEGACY_DIR = "nba_data/legacy_raw"
os.makedirs(LEGACY_DIR, exist_ok=True)

# Season Definitions (Regular Season Approx dates)
SEASONS = {
    "1996-97": ("19961101", "19970420"), # Jordan Era
    "1997-98": ("19971031", "19980419"),
    "1998-99": ("19990205", "19990505"), # Lockout
    "2002-03": ("20021029", "20030416"), # MJ Final, Yao Rookie
    "2003-04": ("20031028", "20040414"), # LeBron Rookie
    "2005-06": ("20051101", "20060419"), # Kobe 81
    "2009-10": ("20091027", "20100414"), # Kobe Last Ring
}

def get_dates_between(start_str, end_str):
    start = datetime.strptime(start_str, "%Y%m%d")
    end = datetime.strptime(end_str, "%Y%m%d")
    date_list = []
    
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y%m%d"))
        curr += timedelta(days=1)
    return date_list

def process_date(date_str):
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        events = data.get('events', [])
        
        if not events: return 0
        
        saved_count = 0
        for event in events:
            game_id = event['id']
            # Fetch full summary which has boxscore
            sum_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            try:
                s_resp = requests.get(sum_url, timeout=10)
                s_data = s_resp.json()
                
                # Check if it has stats
                if 'boxscore' in s_data or 'leaders' in s_data:
                    # Save
                    with open(os.path.join(LEGACY_DIR, f"legacy_{game_id}.json"), 'w') as f:
                        json.dump(s_data, f)
                    saved_count += 1
            except:
                pass
                
        return saved_count
            
    except Exception as e:
        print(f"Error {date_str}: {e}")
        return 0

def run_collector():
    print("🕰️  Starting Mass Legacy Data Resurrection (1996-2010)...")
    
    for season, (start, end) in SEASONS.items():
        print(f"\n📚 Processing Season {season} ({start}-{end})...")
        dates = get_dates_between(start, end)
        
        total_saved = 0
        for d in dates:
            count = process_date(d)
            total_saved += count
            # print(f"   {d}: {count} games", end="\r") 
            # Minimal output to avoid cluttering logs
        
        print(f"   ✅ Season {season} Complete. Saved {total_saved} games.")

if __name__ == "__main__":
    run_collector()
