
import duckdb
import argparse
from datetime import datetime, timedelta
import sys
import os

# Import Layers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from layers import layer_momentum, layer_pace, layer_player_form, layer_matchup, layer_injury, layer_schedule, layer_advanced, layer_composite

DB_PATH = "/Users/js/g9/nba_analytics.duckdb"

def get_daily_scores(target_date, db_path=DB_PATH):
    print(f"Running Quant Engine for {target_date}...")
    con = duckdb.connect(db_path)
    
    # 1. Get Scheduled Games
    games = con.execute(f"SELECT game_id, home_id, away_id FROM dim_schedule WHERE game_date = '{target_date}'").fetchall()
    print(f"Found {len(games)} games.")
    
    results = []
    
    for g in games:
        gid, home, away = g
        # print(f"Processing Game {gid}...") 
        
        # --- HOME ---
        h_stats = {
            "momentum": layer_momentum.calculate_momentum(target_date, home, con),
            "pace": layer_pace.calculate_pace(target_date, home, con),
            "star_form": layer_player_form.calculate_player_form(target_date, home, con),
            "matchup": layer_matchup.calculate_matchup(target_date, home, away, con), 
            "injury_impact": layer_injury.calculate_injury_impact(target_date, home, con),
            "schedule_stress": layer_schedule.calculate_schedule_stress(target_date, home, con),
            "clutch": layer_advanced.calculate_clutch(target_date, home, con),
            "defense": layer_advanced.calculate_defense(target_date, home, con),
            "variance": layer_advanced.calculate_variance(target_date, home, con),
            "psych": layer_advanced.calculate_psych(target_date, home, con)
        }
        
        # --- AWAY ---
        a_stats = {
            "momentum": layer_momentum.calculate_momentum(target_date, away, con),
            "pace": layer_pace.calculate_pace(target_date, away, con),
            "star_form": layer_player_form.calculate_player_form(target_date, away, con),
            "matchup": layer_matchup.calculate_matchup(target_date, away, home, con),
            "injury_impact": layer_injury.calculate_injury_impact(target_date, away, con),
            "schedule_stress": layer_schedule.calculate_schedule_stress(target_date, away, con),
            "clutch": layer_advanced.calculate_clutch(target_date, away, con),
            "defense": layer_advanced.calculate_defense(target_date, away, con),
            "variance": layer_advanced.calculate_variance(target_date, away, con),
            "psych": layer_advanced.calculate_psych(target_date, away, con)
        }
        
        # Composite
        h_comp = layer_composite.calculate_composite(h_stats)
        a_comp = layer_composite.calculate_composite(a_stats)

        # Output Struct
        match_data = {
            "game_id": gid,
            "home_id": home,
            "away_id": away,
            "home_stats": h_stats,
            "away_stats": a_stats,
            "home_score": h_comp,
            "away_score": a_comp,
            # Placeholder for Quant result if we were running full cache_engine here
            # In production, daily_quant_engine should probably UNIFY with cache_engine logic
            # For now, we assume this script is mostly for Data Layer generation.
            # But wait, layer_narrative needs 'market_data' which comes from cache_engine.analyze_matchup
        }
        results.append(match_data)
        
    con.close()
    return results

# Note: The true integration happens in 'run_daily_analysis.py' or 'rerun_report.py'
# where both Data Layer and Quant Engine (Cache) meet.
# 'daily_quant_engine.py' currently just builds the raw stats layers.
# We should update 'rerun_report.py' instead for the immediate test, 
# or ensure daily_quant_engine calls analyze_matchup.

def main():
    pass # Kept as is for now

if __name__ == "__main__":
    main()
