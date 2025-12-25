
import json
import pandas as pd
import sys
import os

# Import Engine
sys.path.append(os.getcwd())
from quant_engine_v1.trap_engine import TrapEngine

INPUT_FILE = "processed/nba_regime_index_v1.json"

def run_test():
    print("💣 Initializing TRAP ENGINE Test (2023-24)...")
    
    # 1. Load Data
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
        
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['edge_score'] = pd.to_numeric(df['edge_score'], errors='coerce')
    df['fav_pct'] = pd.to_numeric(df['fav_pct'], errors='coerce')
    
    # Filter 2023-24 Season (approx Oct 2023 - June 2024)
    start_date = "2023-10-24"
    end_date = "2024-06-20"
    mask_season = (df['date'] >= start_date) & (df['date'] <= end_date)
    season_df = df[mask_season].copy()
    
    print(f"📉 Loaded Season Data: {len(season_df)} games")
    
    # 2. Run Engine
    engine = TrapEngine()
    results = engine.run_batch(season_df)
    
    if results.empty:
        print("⚠️ No games met the Universe criteria (Edge 65-80). Check filter.")
        return

    # 3. Analyze Performance
    # We want to see if HARD_TRAP games collapsed.
    
    print(f"\n🎯 Universe (Edge 65-80): {len(results)} games")
    
    summary = (
        results
        .groupby("trap_level")
        .agg(
            count=("id", "count"),
            collapse_rate=("regime_type", lambda x: (x == "Favorite_Collapse").mean()),
            upset_rate=("regime_type", lambda x: (x == "Underdog_Upset").mean()),
            win_rate=("result", lambda x: (x == "Win").mean())
        )
        .sort_values("count", ascending=False)
    )
    
    print("\n📊 TRAP LEVEL PERFORMANCE:")
    print(summary.to_string(float_format="{:.1%}".format))
    
    # Check specifically HARD TRAP
    if "HARD_TRAP" in summary.index:
        hard_collapse = summary.loc["HARD_TRAP", "collapse_rate"]
        print(f"\n🔥 HARD TRAP Collapse Rate: {hard_collapse:.1%}")
        if hard_collapse > 0.25:
             print("✅ SUCCESS: Exceeds 25% Threshold.")
        else:
             print("❌ FAILURE: Below 25% Threshold.")

    # Save details
    results.to_csv("reports/trap_engine_test_23_24.csv", index=False)
    print("\n💾 Details saved to reports/trap_engine_test_23_24.csv")

if __name__ == "__main__":
    run_test()
