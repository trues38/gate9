import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.ingest.fetch_market_data import get_market_vector
from regime_zero.ingest.fetch_headlines import get_daily_headlines
from regime_zero.embedding.vectorizer import vectorize_market_state

OUTPUT_FILE = "regime_zero/data/history_vectors.jsonl"

def build_history(start_date, end_date):
    """
    Iterates through dates, generates vectors, and saves them.
    """
    print(f"📚 [Regime Zero] Building History from {start_date} to {end_date}...")
    
    current_date = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    
    # Check if file exists to append or overwrite? 
    # For now, let's append if exists, but maybe we should handle duplicates.
    # Simple approach: Append.
    
    with open(OUTPUT_FILE, "a") as f:
        while current_date <= end_date_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Skip weekends? Market data might be empty, but news exists.
            # Let's try every day.
            
            print(f"Processing {date_str}...")
            
            # 1. Get Data
            market_data = get_market_vector(date_str)
            headlines = get_daily_headlines(date_str)
            
            # Check if we have enough data to be meaningful
            # If no market data AND no headlines, skip
            has_market = any(v is not None for v in market_data.values())
            has_news = len(headlines) > 0
            
            if not has_market and not has_news:
                print(f"⚠️ Skipping {date_str}: No data.")
                current_date += timedelta(days=1)
                continue
                
            # 2. Vectorize
            try:
                vector, prompt = vectorize_market_state(date_str, market_data, headlines)
                
                # 3. Save
                record = {
                    "date": date_str,
                    "vector": vector,
                    "prompt_preview": prompt[:200],
                    "meta": {
                        "market_data_count": sum(1 for v in market_data.values() if v),
                        "headline_count": len(headlines)
                    }
                }
                f.write(json.dumps(record) + "\n")
                f.flush() # Ensure write
                print(f"✅ Saved {date_str}")
                
            except Exception as e:
                print(f"❌ Error processing {date_str}: {e}")
            
            current_date += timedelta(days=1)

if __name__ == "__main__":
    # Test run for a few days
    # Default to last 7 days for demo
    end = datetime.now()
    start = end - timedelta(days=5)
    
    build_history(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
