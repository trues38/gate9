import os
import sys
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load Environment Variables
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def fetch_and_upsert_prices():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials not found.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🚀 Fetching Real Price Data from Yahoo Finance...")
    
    # Tickers to fetch
    # SPY: S&P 500
    # QQQ: Nasdaq 100
    # ^KS11: KOSPI
    # ^KQ11: KOSDAQ
    tickers = {
        "SPY": "SPY",
        "QQQ": "QQQ",
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "NVDA": "NVDA", # Representative Tech
        "AAPL": "AAPL",
        "TSLA": "TSLA",
        "005930.KS": "005930.KS" # Samsung Electronics
    }
    
    start_date = "2000-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    all_records = []
    
    for name, symbol in tickers.items():
        print(f"   Fetching {name} ({symbol})...")
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if df.empty:
                print(f"   ⚠️ No data for {name}")
                continue
            
            # Debug: Print first few rows and columns
            print(f"   DEBUG: Columns for {name}: {df.columns}")
            print(df.head(2))

            # Handle MultiIndex columns if present (e.g. ('Close', 'SPY'))
            if isinstance(df.columns, pd.MultiIndex):
                print("   ℹ️ Detected MultiIndex columns. Flattening...")
                # If level 1 is the ticker, we can drop it or just select the level 0
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception as e:
                    print(f"   ⚠️ Failed to flatten columns: {e}")

            # Reset index to get Date
            df = df.reset_index()
            
            # Prepare records
            for _, row in df.iterrows():
                # Check for header rows masquerading as data (unlikely with yf, but possible if CSV read)
                if row['Date'] == 'Ticker':
                    continue
                    
                # yfinance columns might be MultiIndex if multiple tickers, but here we fetch one by one.
                # Columns: Date, Open, High, Low, Close, Adj Close, Volume
                
                # Check if 'Close' is scalar or Series (sometimes yfinance returns weird shapes)
                close_val = row['Close']
                if hasattr(close_val, 'item'):
                    close_val = close_val.item()
                
                # Handle Date
                date_val = row['Date']
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val).split(' ')[0]
                
                record = {
                    "ticker": name, # Use our internal name (SPY, KOSPI) or symbol? Let's use symbol or standardized name.
                                    # The backtest engine likely looks for specific tickers.
                                    # Let's use the key as ticker.
                    "date": date_str,
                    "close": float(close_val),
                    "volume": int(row['Volume']) if 'Volume' in row else 0,
                    "open": float(row['Open']) if 'Open' in row else 0.0,
                    "high": float(row['High']) if 'High' in row else 0.0,
                    "low": float(row['Low']) if 'Low' in row else 0.0
                }
                all_records.append(record)
                
        except Exception as e:
            print(f"   ❌ Error fetching {name}: {e}")
            
    print(f"   Total records fetched: {len(all_records)}")
    
    # Batch Upsert
    batch_size = 1000
    print(f"💾 Upserting to price_daily in batches of {batch_size}...")
    
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i+batch_size]
        try:
            supabase.table("price_daily").upsert(batch).execute()
            print(f"   Upserted batch {i//batch_size + 1}/{len(all_records)//batch_size + 1}...", end='\r')
        except Exception as e:
            print(f"   ❌ Batch Error: {e}")
            
    print("\n✅ Real Price Data Sync Complete.")

if __name__ == "__main__":
    fetch_and_upsert_prices()
