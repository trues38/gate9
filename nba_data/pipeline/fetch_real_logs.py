
import requests
import json
import duckdb
import time
import os

# Create dir
os.makedirs("nba_data/gamelogs_real", exist_ok=True)

# Connect
con = duckdb.connect("nba_analytics.duckdb", read_only=True)
# Fetch rosters for TOR(28) and NY(18) and PHI(20) just in case
roster = con.sql("SELECT player_id, name, team_id FROM fact_rosters").fetchall()
con.close()

# IDs
# ESPN Player ID is needed. `fact_rosters` has `player_id`.

for pid, name, tid in roster:
    print(f"Fetching logs for {name} ({pid})...")
    try:
        # Correct Endpoint found via search
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{pid}/gamelog"
        
        # User Agent often helps
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
             print(f"   Error fetching {name}: {resp.status_code}")
             continue
             
        data = resp.json()
        
        # Parse Events
        # season -> leagues -> events
        events = []
        # ESPN API structure varies for gamelog.
        # Usually: params -> season -> type -> ...
        # Let's clean the full response for calculation
        
        # Save Raw first
        fname = f"nba_data/gamelogs_real/{name.replace(' ', '_')}_{pid}.json"
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        print(f"Failed {name}: {e}")
    
    time.sleep(0.5) 
