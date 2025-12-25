import duckdb
import pandas as pd
import json
import tqdm
import sys
import os

# Add path for engine imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine_v1.rdata_engine import RDataEngine
from quant_engine_v1.profile_engine import ProfileEngine

OUTPUT_PATH = "processed/regime_vectors_v1.json"

def generate_vectors():
    print("🚀 Starting Vector Generation (Phase 27)...")
    
    # Init Engines
    rdata = RDataEngine()
    profiler = ProfileEngine()
    
    # Load All Games (Treasury)
    # Use read_only=True to avoid locking if RDataEngine also opens it
    con = duckdb.connect('nba_sql.duckdb', read_only=True)
    games_df = con.sql("SELECT Date, Team, Opponent, game_id, Points, OpponentPoints, V FROM rdata_treasury ORDER BY Date ASC").df()
    con.close()
    
    print(f"loaded {len(games_df)} games from Treasury.")
    
    vectors = []
    
    # Iterate with Progress Bar
    # Use tqdm if available, else simple loop
    iterator = tqdm.tqdm(games_df.iterrows(), total=len(games_df))
    
    for idx, row in iterator:
        try:
            date_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            team = row['Team']
            opp = row['Opponent']
            
            # 1. Fetch RData Metrics
            # We use analyze_matchup manually to get the raw metrics
            # But analyze_matchup is designed for prediction (before game).
            # We want the state entering the game.
            # analyze_matchup correctly fetches 'latest metrics' relative to date.
            
            # Note: This is computationally expensive (SQL query per row).
            # For 38,000 rows, this might take 1-2 hours via iterative SQL.
            # Optimization: We should probably fetch ALL metrics in bulk via SQL first, 
            # but RDataEngine logic is complex.
            # Let's try doing a batch of recent 5000 games first to verify, or run full if acceptable.
            # Or use the 'features_2025.csv' logic but applied to history?
            # Creating 'processed/features_unifed.csv' (Treasury + Metrics) would be best.
            
            # FOR NOW: Let's rely on RDataEngine but anticipate slowness. 
            # Or just do the last 10 years (approx 25,000 games).
            
            # Actually, RDataEngine.analyze_matchup does a lot.
            # Let's see if we can optimize.
            
            # Run Analysis
            analysis = rdata.analyze_matchup(team, opp, date_str)
            if not analysis:
                continue
                
            # Run Profiler to get Scores
            profiles = profiler.build_profiles(analysis)
            
            # Extract 5D Vector
            # Flow Score is in 'FLOW' -> 'strength' (or raw evidence?)
            # Profile object: { 'FLOW': {'state': ..., 'score': 6.9, ...} }
            # Wait, ProfileEngine returns a dict of ProfileResult objects or dicts?
            # It returns a dict of dicts usually. Let's check ProfileEngine code.
            
            # Assuming structure based on report:
            # profiles['FLOW'].score (we need to ensure score is accessible)
            
            # Let's extract scores safely
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
                'res': int(row['V']) # Result (Win/Loss) for context
            }
            
            vectors.append(vec)
            
        except Exception as e:
            # print(f"Error on {date_str} {team}: {e}")
            continue
            
    # Save
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(vectors, f)
        
    print(f"✅ Generated {len(vectors)} vectors -> {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_vectors()
