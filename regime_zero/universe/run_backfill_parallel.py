import sys
import os
import json
import time
import threading
from datetime import datetime, timedelta
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.universe.generate_regimes import generate_regime_for_date

OUTPUT_FILE = "regime_zero/data/regime_objects.jsonl"
file_lock = threading.Lock()

def process_date(date_str):
    try:
        regime = generate_regime_for_date(date_str)
        if regime:
            with file_lock:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(json.dumps(regime) + "\n")
                    f.flush()
            return f"✅ {date_str}: {regime['regime_name']}"
        else:
            return f"⚠️ {date_str}: No regime generated."
    except Exception as e:
        return f"❌ {date_str}: Error {e}"

def run_parallel_backfill(start_date, end_date, workers=10):
    current_date = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    
    dates = []
    while current_date <= end_date_dt:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
        
    print(f"🚀 Starting Parallel Backfill for {len(dates)} days with {workers} workers...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_date = {executor.submit(process_date, date): date for date in dates}
        
        for future in as_completed(future_to_date):
            date = future_to_date[future]
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"❌ {date} generated an exception: {e}")

if __name__ == "__main__":
    # Calculate dates for the last 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    run_parallel_backfill(start_str, end_str, workers=10)
