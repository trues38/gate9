import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.universe.generate_regimes import run_backfill

if __name__ == "__main__":
    # Calculate dates for the last 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"🚀 Starting 1-Year Regime Backfill: {start_str} to {end_str}")
    
    # Run backfill
    run_backfill(start_str, end_str)
    
    print("✅ Backfill Complete!")
