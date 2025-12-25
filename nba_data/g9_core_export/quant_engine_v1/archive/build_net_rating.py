import duckdb
import pandas as pd
import json
import os

DB_PATH = '/Users/js/g9/nba_analytics.duckdb'
CACHE_FILE = 'quant_engine_v1/quant_cache/net_rating.json'

def build_net_rating():
    print("🚀 Building Net Rating Cache (Calculated from Gamelogs)...")
    
    con = duckdb.connect(DB_PATH)
    
    # Logic:
    # 1. Aggregate Player Points to get Team Points per Game.
    # 2. Self-Join to get Opponent Points.
    # 3. Calculate Margin.
    
    query = """
    WITH team_games AS (
        SELECT 
            game_id,
            team_id,
            MAX(game_date) as game_date, -- Use MAX to pick one date per group
            SUM(pts) as team_pts
        FROM fact_gamelogs
        GROUP BY game_id, team_id
        HAVING SUM(pts) > 60
    )
    SELECT 
        t1.team_id,
        t1.game_date,
        t1.team_pts as pts,
        t2.team_pts as opp_pts,
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
        print("⚠️ No data found in fact_gamelogs.")
        return

    cache = {}
    
    for team_id, group in df.groupby('team_id'):
        season_net = group['margin'].mean()
        l10_net = group.tail(10)['margin'].mean()
        
        cache[str(team_id)] = {
            "season": round(season_net, 1),
            "l10": round(l10_net, 1),
            "games": len(group)
        }
        
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
        
    print(f"✅ Net Rating Cache Updated (from {len(df)} game-team records).")

if __name__ == "__main__":
    build_net_rating()
