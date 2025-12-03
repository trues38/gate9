import sys
import os
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.engine.run_consensus_pipeline import run_pipeline

def run_backfill(days=10):
    print(f"🚀 STARTING SALES BACKFILL ({days} Days)")
    print("="*50)
    
    # Start from yesterday (2025-12-01) backwards
    # Or from today? User said "from today go back 10 days".
    # Assuming today is 2025-12-02, we want 12-01, 11-30...
    # Actually, user said "today's pipeline report... from today 10 days back".
    # Let's do 2025-12-01 back to 2025-11-22.
    
    base_date = datetime(2025, 12, 1) # Start from the date we just verified
    
    for i in range(days):
        target_date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"\n📅 PROCESSING DATE: {target_date} ({i+1}/{days})")
        
        try:
            run_pipeline(target_date)
            print(f"✅ Completed {target_date}")
        except Exception as e:
            print(f"❌ Failed {target_date}: {e}")
            
        # Small pause to be nice to APIs
        time.sleep(2)
        
    print("\n🎉 SALES BACKFILL COMPLETE!")

if __name__ == "__main__":
    run_backfill()
