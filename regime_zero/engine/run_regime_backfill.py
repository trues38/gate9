import sys
import os
import json
import pandas as pd
from datetime import datetime
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.engine.regime_generator import RegimeGenerator
from regime_zero.config.economy_config import ECONOMY_CONFIG

HISTORY_FILE = "regime_zero/data/multi_asset_history/unified_history.csv"
OUTPUT_FILE = "regime_zero/data/regime_objects.jsonl"

def run_backfill(limit_days=None):
    print(f"🚀 Starting Regime Backfill (Tongyi DeepResearch)...")
    
    # 1. Load History Dates
    if not os.path.exists(HISTORY_FILE):
        print("❌ No history file found.")
        return
        
    df = pd.read_csv(HISTORY_FILE)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    unique_dates = df['date'].dropna().unique()
    unique_dates = sorted(unique_dates, reverse=True) # Newest first
    
    print(f"📅 Found {len(unique_dates)} unique dates in history.")
    
    # 2. Check Existing Regimes to Resume
    existing_dates = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    # We need to check if ALL assets are done for this date?
                    # For simplicity, let's just track (date, asset) tuples
                    existing_dates.add((r['date'], r['asset']))
                except:
                    pass
    
    print(f"📚 Found {len(existing_dates)} existing regime entries.")
    
    # 3. Initialize Generator
    generator = RegimeGenerator(ECONOMY_CONFIG)
    
    # 4. Iterate
    processed_count = 0
    
    for date_ts in tqdm(unique_dates):
        target_date = pd.to_datetime(date_ts).strftime("%Y-%m-%d")
        
        # Limit check
        if limit_days and processed_count >= limit_days:
            break
            
        # For each asset
        for asset in ECONOMY_CONFIG.assets:
            if (target_date, asset) in existing_dates:
                continue # Skip if already done
                
            print(f"\n⚙️ Generating {asset} for {target_date}...")
            regime = generator.generate_regime(asset, target_date)
            
            if regime:
                # Save to Master Object File immediately
                with open(OUTPUT_FILE, "a") as f:
                    # Add metadata for "Backfill"
                    regime['source'] = "backfill_tongyi"
                    f.write(json.dumps(regime) + "\n")
                
                existing_dates.add((target_date, asset))
                processed_count += 1
            else:
                print(f"⚠️ Failed/No Data for {asset} on {target_date}")

    print("\n🎉 Backfill Complete!")

if __name__ == "__main__":
    # Default to backfilling last 30 days for test, or user can change
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill")
    args = parser.parse_args()
    
    run_backfill(args.days)
