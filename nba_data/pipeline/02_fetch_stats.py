import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats
import time
import os
import random

# Step 2: Fetch Season Stats (2009-2025)
# Goal: Get aggregated player stats for each season.
# We will use LeagueDashPlayerStats endpoint.

DATA_DIR = "/Users/js/g9/nba_data/seasons"
SEASONS = [f"{y}-{str(y+1)[-2:]}" for y in range(2009, 2025)]

def fetch_season_stats():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for season in SEASONS:
        output_file = os.path.join(DATA_DIR, f"season_stats_{season}.csv")
        if os.path.exists(output_file):
            print(f"Skipping {season}, already exists.")
            continue
            
        print(f"Fetching stats for {season}...")
        try:
            # MeasureType="Base" gives standard stats
            # PerMode="PerGame" or "Totals". Let's get Totals or PerGame? 
            # Usually PerGame is better for quick analysis, but Totals allows calculation.
            # Let's get Totals and we can calculate per game if needed, or get PerGame.
            # Spec said: gp, min, pts, reb, ast... 
            # Let's fetch 'Base' and 'Advanced' if possible, but start with Base.
            
            # Fetch Base Stats
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed='PerGame' 
            )
            df = stats.get_data_frames()[0]
            
            # Save to CSV
            df.to_csv(output_file, index=False)
            print(f"Saved {season} stats: {len(df)} players.")
            
            # Sleep to be nice to API
            time.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            print(f"Error fetching {season}: {e}")
            time.sleep(5) # Wait longer on error

if __name__ == "__main__":
    fetch_season_stats()
