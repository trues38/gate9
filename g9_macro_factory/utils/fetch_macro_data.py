import os
import sys
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load Environment Variables
load_dotenv(override=True)

FRED_API_KEY = os.getenv("FRED_API_KEY")

def fetch_macro_data():
    if not FRED_API_KEY:
        print("❌ FRED_API_KEY not found in .env")
        return

    print("🚀 Fetching Macro Indicators from FRED...")
    
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()
    
    # Series IDs
    series_map = {
        "us10y": "DGS10",       # 10-Year Treasury Constant Maturity Rate
        "dxy": "DTWEXBGS",      # Trade Weighted U.S. Dollar Index: Broad Goods and Services
        "wti": "DCOILWTICO",    # Crude Oil Prices: West Texas Intermediate (WTI)
        "vix": "VIXCLS",        # CBOE Volatility Index: VIX
        "cpi": "CPIAUCSL",      # Consumer Price Index for All Urban Consumers: All Items (Monthly)
        "usdkrw": "DEXKOUS"     # South Korean Won to U.S. Dollar Spot Exchange Rate
    }
    
    dfs = []
    
    for name, series_id in series_map.items():
        print(f"   Fetching {name} ({series_id})...")
        try:
            df = web.DataReader(series_id, 'fred', start_date, end_date, api_key=FRED_API_KEY)
            df = df.rename(columns={series_id: name})
            dfs.append(df)
        except Exception as e:
            print(f"   ⚠️ Failed to fetch {name}: {e}")
            
    if not dfs:
        print("❌ No data fetched.")
        return

    # Merge all
    print("   Merging data...")
    combined_df = pd.concat(dfs, axis=1)
    
    # Forward fill (especially for CPI which is monthly, and weekends)
    # But wait, we want daily business days usually.
    # Let's reindex to daily range and ffill.
    
    full_idx = pd.date_range(start=start_date, end=end_date, freq='D')
    combined_df = combined_df.reindex(full_idx)
    
    # Forward fill missing values (e.g. weekends, holidays, monthly CPI)
    combined_df = combined_df.ffill()
    
    # Reset index to get 'date' column
    combined_df = combined_df.reset_index().rename(columns={'index': 'date'})
    
    # Filter out rows where all columns are NaN (start of period before data exists)
    combined_df = combined_df.dropna(how='all', subset=series_map.keys())
    
    # Save to CSV
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "macro_indicators.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    combined_df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(combined_df)} rows to {output_path}")
    print(combined_df.tail())

if __name__ == "__main__":
    fetch_macro_data()
