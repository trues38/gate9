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
        # generate_regime_for_date handles data fetching internally.
        # For 1970-1999, get_market_vector will return None/Empty, 
        # but get_daily_headlines will return news.
        # We need to ensure generate_regime_for_date doesn't bail if market_data is empty but news exists.
        
        regime = generate_regime_for_date(date_str)
        if regime:
            with file_lock:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(json.dumps(regime) + "\n")
                    f.flush()
            return f"✅ {date_str}: {regime['regime_name']}"
        else:
            # Silence "No data" warnings for weekends/holidays to reduce noise
            return None 
    except Exception as e:
        return f"❌ {date_str}: Error {e}"

def run_massive_backfill(start_year, end_year, workers=50):
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    # Filter out future dates
    if end_date > datetime.now():
        end_date = datetime.now()
        
    current_date = start_date
    dates = []
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
        
    print(f"🚀 Starting MASSIVE Backfill: {start_year} to {end_year}")
    print(f"📅 Total Days: {len(dates)}")
    print(f"⚡️ Workers: {workers}")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_date = {executor.submit(process_date, date): date for date in dates}
        
        completed = 0
        for future in as_completed(future_to_date):
            date = future_to_date[future]
            completed += 1
            try:
                result = future.result()
                if result:
                    print(f"[{completed}/{len(dates)}] {result}")
                elif completed % 100 == 0:
                    print(f"[{completed}/{len(dates)}] Progress...")
            except Exception as e:
                print(f"❌ {date} generated an exception: {e}")

if __name__ == "__main__":
    # 1970 to 2025
    run_massive_backfill(1970, 2025, workers=50)
