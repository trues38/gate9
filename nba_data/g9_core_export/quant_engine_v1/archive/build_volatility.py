import duckdb
import pandas as pd
import json
import os
import numpy as np

DB_PATH = '/Users/js/g9/nba_analytics.duckdb'
CACHE_FILE = 'quant_engine_v1/quant_cache/volatility.json'

def build_volatility():
    print("🚀 Building Volatility Cache (Calculated from Gamelogs)...")
    con = duckdb.connect(DB_PATH)
    
    query = """
    WITH team_games AS (
        SELECT 
            game_id,
            team_id,
            MAX(game_date) as game_date,
            SUM(pts) as team_pts
        FROM fact_gamelogs
        GROUP BY game_id, team_id
        HAVING SUM(pts) > 60
    )
    SELECT 
        t1.team_id,
        (t1.team_pts - t2.team_pts) as margin
    FROM team_games t1
    JOIN team_games t2 ON t1.game_id = t2.game_id AND t1.team_id != t2.team_id
    ORDER BY t1.team_id, t1.game_date ASC
    """
    
    try:
        df = con.execute(query).df()
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return

    if df.empty:
        print("⚠️ No data found.")
        return

    cache = {}
    for team_id, group in df.groupby('team_id'):
        vol_season = group['margin'].std()
        if pd.isna(vol_season): vol_season = 10.0
        cache[str(team_id)] = round(vol_season, 1)
        
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
        
    print(f"✅ Volatility Cache Updated (from {len(df)} game-team records).")

if __name__ == "__main__":
    build_volatility()
