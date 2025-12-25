import duckdb
import pandas as pd
import json
import tqdm
import sys
import os
import time

# Add path for engine imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine_v1.rdata_engine import RDataEngine
from quant_engine_v1.profile_engine import ProfileEngine

OUTPUT_PATH = "processed/regime_vectors_v1.json"

def generate_vectors_safe():
    print("🚀 Starting Vector Generation (Safe Mode)...")
    
    # 1. Load Data FIRST (Close DB immediately)
    print("Loading Data...")
    con = duckdb.connect('nba_sql.duckdb', read_only=True)
    games_df = con.sql("SELECT Date, Team, Opponent, game_id, Points, OpponentPoints, V FROM rdata_treasury ORDER BY Date ASC").df()
    con.close()
    print(f"Loaded {len(games_df)} games.")
    
    # 2. Init Engines (RDataEngine will open its own connection)
    rdata = RDataEngine() # Opens self.conn
    profiler = ProfileEngine()
    
    vectors = []
    
    # 3. Iterate
    # Limit to last 3 seasons for rapid prototyping (Approx 3500 games)
    print("limiting to 2023+ for Phase 27 Prototype...")
    games_df = games_df[games_df['Date'] >= '2023-01-01']
    
    print(f"Processing {len(games_df)} games...")
    
    start_time = time.time()
    for idx, row in tqdm.tqdm(games_df.iterrows(), total=len(games_df)):
        try:
            date_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            team = row['Team']
            opp = row['Opponent']
            
            # Analyze
            # RDataEngine uses internal duckdb conn.
            # analyze_matchup is optimized now (uses SQL).
            analysis = rdata.analyze_matchup(team, opp, date_str)
            
            if not analysis:
                continue
                
            # Profile
            p_data = profiler.build_profiles(analysis)
            profiles = p_data # ProfileEngine.build_profiles returns dict directly now
            
            # Extract
            vec = {
                'id': row['game_id'] or f"{date_str}_{team}_{opp}",
                'date': date_str,
                'team': team,
                'opp': opp,
                'v': [
                    profiles['FLOW'].get('score', 0),
                    profiles['FATIGUE'].get('score', 0),
                    profiles['MEMORY'].get('score', 0),
                    profiles['LUCK'].get('score', 0),
                    profiles['TEMPO'].get('score', 0)
                ],
                'res': int(row['V'])
            }
            vectors.append(vec)
            
        except Exception as e:
            # print(f"Skip {date_str} {team}: {e}")
            pass
            
    # Save
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(vectors, f)
        
    print(f"✅ Generated {len(vectors)} vectors -> {OUTPUT_PATH}")
    print(f"Time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    generate_vectors_safe()
