import argparse
from datetime import datetime, timedelta
from regime_zero.engine.regime_generator import RegimeGenerator
import pandas as pd

def backfill_regimes(start_date, end_date):
    generator = RegimeGenerator()
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    current_dt = start_dt
    while current_dt <= end_dt:
        target_date = current_dt.strftime("%Y-%m-%d")
        print(f"\n📅 Processing {target_date}...")
        
        for asset in ["BTC", "FED", "OIL", "GOLD", "NEWS"]:
            # Check if already exists (optional optimization, skipping for now to ensure overwrite)
            generator.generate_regime(asset, target_date)
            
        current_dt += timedelta(days=1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-11-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-12-03", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    backfill_regimes(args.start, args.end)
