import sys
import os
import time
from datetime import datetime, timedelta
import calendar

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.reporting.generate_continuous_report import generate_report

def run_backfill(days=60):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date
    
    print(f"🚀 Starting Backfill from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n📅 Processing {date_str}...")
        
        # 1. Generate Daily Report
        try:
            generate_report(date_str, "daily")
        except Exception as e:
            print(f"❌ Daily Failed: {e}")
            
        # 2. Generate Weekly Report (Fridays)
        if current_date.weekday() == 4: # Friday
            try:
                print(f"   Weekly Report Triggered.")
                generate_report(date_str, "weekly")
            except Exception as e:
                print(f"❌ Weekly Failed: {e}")

        # 3. Generate Monthly Report (Last Day of Month)
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        if current_date.day == last_day:
            try:
                print(f"   Monthly Report Triggered.")
                generate_report(date_str, "monthly")
            except Exception as e:
                print(f"❌ Monthly Failed: {e}")
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # Sleep slightly to avoid overwhelming API if needed, though we have retry logic
        time.sleep(1)

if __name__ == "__main__":
    days = 60
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    run_backfill(days)
