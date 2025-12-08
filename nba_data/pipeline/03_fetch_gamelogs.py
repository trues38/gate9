import pandas as pd
from nba_api.stats.endpoints import playergamelog
import json
import os
import time
import random

# Step 3: Fetch Game Logs
# Goal: Fetch game logs for target players for all relevant seasons (2009-2025).

DATA_DIR = "/Users/js/g9/nba_data/gamelogs"
PLAYER_FILE = "/Users/js/g9/nba_data/players/master_list.json"
SEASONS = [f"{y}-{str(y+1)[-2:]}" for y in range(2009, 2025)]

def fetch_game_logs():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Load player list
    if not os.path.exists(PLAYER_FILE):
        print("Player list not found. Run Step 1 first.")
        return

    with open(PLAYER_FILE, "r") as f:
        players = json.load(f)
        
    print(f"Loaded {len(players)} players.")
    
    # For now, let's just create the folder structure and fetch for first 5 players as a test
    # or iterate all but handle errors gracefully.
    
    # We need to filter players who are worth fetching? 
    # The spec say: "Start with 2025 roster, fetch their history".
    
    for i, player in enumerate(players):
        pid = player['player_id']
        pname = player['name']
        print(f"[{i+1}/{len(players)}] Processing {pname} ({pid})...")
        
        player_dir = os.path.join(DATA_DIR, str(pid))
        os.makedirs(player_dir, exist_ok=True)
        
        for season in SEASONS:
            output_file = os.path.join(player_dir, f"gamelog_{season}.csv")
            if os.path.exists(output_file):
                continue
                
            try:
                # Fetch game log
                gl = playergamelog.PlayerGameLog(player_id=pid, season=season)
                df = gl.get_data_frames()[0]
                
                if not df.empty:
                    df.to_csv(output_file, index=False)
                    # print(f"  Saved {season}: {len(df)} games.")
                else:
                    # Mark as empty so we don't retry? Or just skip saving.
                    # print(f"  No games for {season}.")
                    pass
                
                time.sleep(random.uniform(0.6, 1.2)) # Brief sleep
                
            except Exception as e:
                print(f"  Error {season}: {e}")
                time.sleep(2)

if __name__ == "__main__":
    fetch_game_logs()
