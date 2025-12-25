
import pandas as pd
import duckdb
import os
import sys
import tqdm
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant_engine_v1.rdata_engine import RDataEngine
from quant_engine_v1.profile_engine import ProfileEngine

DB_PATH = 'nba_sql.duckdb'
TREASURY_PATH = 'processed/rdata_treasury.csv'

def run_backtest(start_date='2023-10-01', end_date='2025-06-01'):
    print(f"🔄 Starting Backtest (Factor Isolation) | Range: {start_date} to {end_date}")
    
    # 1. Load Treasury for iteration (The "Truth" we verify against)
    df = pd.read_csv(TREASURY_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter by date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    target_games = df.loc[mask].sort_values('Date')
    
    print(f"📅 Games to Process: {len(target_games)}")
    
    out_path = 'processed/backtest_results_exp1.csv'
    
    # 2. Initialize Engines
    # RDataEngine connects to DuckDB which holds the "Past"
    rdata = RDataEngine() 
    profiler = ProfileEngine()
    
    results = []
    
    # 3. Time Machine Loop
    total_games = len(target_games)
    print(f"🚀 Processing {total_games} games...")
    
    for idx, (index, row) in enumerate(target_games.iterrows()):
        try:
            if idx % 10 == 0:
                print(f"Match {idx}/{total_games}...", flush=True)
                
            game_date = row['Date'].strftime('%Y-%m-%d')
            team = row['Team']
            opp = row['Opponent']
            actual_res = row['V'] # 1=Win, 0=Loss
            actual_margin = row['Points'] - row['OpponentPoints']
            
            # ... (Rest of logic) ...
            
            # Mock Odds (Use actual if available in row, else None)
            odds_pkg = None
            if 'odds' in row and pd.notna(row['odds']):
                try:
                    line = float(row['odds'])
                    odds_pkg = {'spread': line} 
                except:
                    pass
            
            # RUN ANALYSIS
            analysis = rdata.analyze_matchup(team, opp, game_date, odds=odds_pkg)
            
            if not analysis:
                continue
            
            # FLATTEN FOR PROFILE ENGINE (Critical Fix)
            # ProfileEngine expects keys at top level (e.g. 'pace_sea', 'avg_diff_P_32')
            if 'home_stats' in analysis:
                analysis.update(analysis['home_stats'])

            # INJECT OPPONENT METRICS
            if 'away_stats' in analysis:
                a_stats = analysis['away_stats']
                
                # Tempo: We need opponent's seasonal pace
                analysis['pace_sea_opp'] = a_stats.get('Pace_Sea', 100.0)
                # Fatigue: We need opponent's rest days
                analysis['days_since_last_o'] = a_stats.get('days_since_last', 0)
                
            # RUN PROFILE
            p_data = profiler.build_profiles(analysis)
            
            # Collect Data
            entry = {
                'date': game_date,
                'team': team,
                'opp': opp,
                'result': actual_res,
                'margin': actual_margin,
                'flow_score': p_data['FLOW']['strength'],
                'fatigue_score': p_data['FATIGUE']['strength'],
                'memory_score': p_data['MEMORY']['strength'],
                'luck_score': p_data['LUCK']['strength'],
                'tempo_score': p_data['TEMPO']['strength'],
                'flow_state': p_data['FLOW']['state'],
                'fatigue_state': p_data['FATIGUE']['state'],
                'memory_state': p_data['MEMORY']['state'],
                'luck_state': p_data['LUCK']['state'],
                'tempo_state': p_data['TEMPO']['state'],
                'edge_score': analysis.get('edge_score'),
                'risk_score': analysis.get('risk_score')
            }
            results.append(entry)
            
            # Incremental Save (Every 10)
            if len(results) >= 10:
                temp_df = pd.DataFrame(results)
                header = not os.path.exists(out_path)
                temp_df.to_csv(out_path, mode='a', header=header, index=False)
                results = [] 
                print(f"💾 Saved batch to {out_path}", flush=True)

        except Exception as e:
            print(f"⚠️ Error {game_date} {team}: {e}", flush=True)
            pass
            
    # 4. Save Final Batch
    if results:
        res_df = pd.DataFrame(results)
        header = not os.path.exists(out_path)
        res_df.to_csv(out_path, mode='a', header=header, index=False)
    
    print(f"✅ Backtest Complete. Saved to {out_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, default="2023-10-01", help="Start Date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default="2025-06-01", help="End Date YYYY-MM-DD")
    args = parser.parse_args()
    
    run_backtest(start_date=args.start, end_date=args.end)
