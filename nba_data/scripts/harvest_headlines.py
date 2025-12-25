
import requests
import json
import time
import os
from datetime import datetime, timedelta

# Output File
OUTPUT_FILE = "data/headlines_2019_2025.jsonl"

# Season Configs (approx start/end to cover reg season + playoffs)
SEASONS = [
    {"start": "2019-10-22", "end": "2020-10-12"}, # Bubble season
    {"start": "2020-12-22", "end": "2021-07-22"},
    {"start": "2021-10-19", "end": "2022-06-20"},
    {"start": "2022-10-18", "end": "2023-06-15"},
    {"start": "2023-10-24", "end": "2024-06-20"},
    {"start": "2024-10-22", "end": "2025-05-01"}  # Until now
]

def fetch_date(date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"⚠️ Net Error {date_str}: {e}")
    return None

def run_harvest():
    # Load existing if any (resume)
    existing_dates = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    existing_dates.add(d['date'])
                except: pass
    
    print(f"📉 Found {len(existing_dates)} processed entries (Note: entries != dates, but checking dates efficiently).")
    
    # We will just append info. To avoid dupe games, we might want to check game_ids.
    # Actually, simpler: just iterate all dates, and verify if we have data for that date.
    # But files are lines of GAMES, not dates.
    # Let's collect processed GAME IDs to be safe.
    processed_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    processed_ids.add(d.get('espn_id'))
                except: pass
    
    print(f"📦 Resuming... {len(processed_ids)} games already harvested.")

    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, 'a') as out_f:
        for season in SEASONS:
            start_dt = datetime.strptime(season["start"], "%Y-%m-%d")
            end_dt = datetime.strptime(season["end"], "%Y-%m-%d")
            
            curr_dt = start_dt
            while curr_dt <= end_dt:
                date_str = curr_dt.strftime("%Y%m%d")
                curr_date_dash = curr_dt.strftime("%Y-%m-%d")
                
                # Basic check: if we have 5-10 games from this date in processed_ids, maybe skip?
                # But ESPN doesn't guarantee fixed IDs. Safer to just run.
                # Optimization: Checking valid date.
                
                print(f"📡 Mining {curr_date_dash}...", end="\r")
                
                data = fetch_date(date_str)
                if data:
                    events = data.get('events', [])
                    for evt in events:
                        g_id = evt.get('id')
                        if g_id in processed_ids:
                            continue
                            
                        # Extract basic info
                        name = evt.get('name') # "Team A at Team B"
                        short_name = evt.get('shortName')
                        
                        # Extract Competitors for mapping
                        comps = evt.get('competitions', [])
                        if not comps: continue
                        
                        competitors = comps[0].get('competitors', [])
                        home_team = next((t['team']['displayName'] for t in competitors if t['homeAway']=='home'), "Unknown")
                        away_team = next((t['team']['displayName'] for t in competitors if t['homeAway']=='away'), "Unknown")
                        winner_id = next((t['id'] for t in competitors if t.get('winner') is True), None)

                        # Extract Headlines (The Gold)
                        headlines = comps[0].get('headlines', [])
                        headline_txt = None
                        headline_desc = None
                        
                        if headlines:
                            headline_txt = headlines[0].get('shortLinkText') or headlines[0].get('description')
                            headline_desc = headlines[0].get('description')
                            
                        # Only save if we have *something* useful? 
                        # User wants 100% coverage. Even if no headline, saving the result/score is useful for verification.
                        # But crucial goal is Narrative.
                        
                        record = {
                            "espn_id": g_id,
                            "date": curr_date_dash,
                            "name": name,
                            "home_team": home_team,
                            "away_team": away_team,
                            "headline": headline_txt,
                            "description": headline_desc,
                            "winner_espn_id": winner_id
                        }
                        
                        out_f.write(json.dumps(record) + "\n")
                        out_f.flush()
                        processed_ids.add(g_id)
                        
                curr_dt += timedelta(days=1)
                time.sleep(0.15) # Be gentle
                
    print("\n✅ Harvest Complete!")

if __name__ == "__main__":
    run_harvest()
