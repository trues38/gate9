import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g9_macro_factory.config import get_supabase_client, TABLE_PRICE_DAILY, TABLE_NEWS

def populate_mock_prices():
    supabase = get_supabase_client()
    print("🎲 Populating Mock Prices...")
    
    # 1. Get Tickers from News
    print("   Fetching tickers from news...")
    # Fetch a sample of news to get tickers
    res = supabase.table(TABLE_NEWS).select("ticker").neq("ticker", "null").limit(10000).execute()
    tickers = list(set([r['ticker'] for r in res.data if r['ticker']]))
    print(f"   Tickers found: {tickers}")
    
    if not tickers:
        print("   ⚠️ No tickers found in news. Using defaults.")
        tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
    else:
        print(f"   Found {len(tickers)} tickers.")
        # Force add common tickers for testing robustness
        common_tickers = ["MSFT", "JACK", "SOFI", "AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "AMD"]
        tickers = list(set(tickers + common_tickers))
        tickers = tickers[:200] # Limit to 200 to cover more ground
        
    # 2. Generate Prices
    # Generate for last 180 days + next 30 days (simulate future)
    end_date = datetime.now().date() + timedelta(days=30)
    start_date = end_date - timedelta(days=210)
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
    
    batch_data = []
    
    for ticker in tickers:
        price = random.uniform(100, 1000)
        trend = random.choice([-0.005, 0.0, 0.005]) # Slight trend
        
        for d in all_dates:
            change_pct = random.normalvariate(trend, 0.02) # 2% volatility
            price = price * (1 + change_pct)
            if price < 1: price = 1
            
            batch_data.append({
                "date": d.isoformat(),
                "ticker": ticker,
                "close": round(price, 2)
            })
            
    # 3. Insert
    print(f"   Inserting {len(batch_data)} price records...")
    
    # Batch insert
    batch_size = 1000
    for i in range(0, len(batch_data), batch_size):
        batch = batch_data[i:i+batch_size]
        try:
            supabase.table(TABLE_PRICE_DAILY).upsert(batch, on_conflict="date,ticker").execute()
            print(f"   Upserted batch {i//batch_size + 1}...", end='\r')
        except Exception as e:
            print(f"   ❌ Batch error: {e}")
            
    print("\n✅ Mock prices populated.")

if __name__ == "__main__":
    populate_mock_prices()
