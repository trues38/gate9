import yfinance as yf
import pandas as pd
import os

def fetch_market_history():
    """Fetches historical price data for key assets."""
    output_dir = "regime_zero/data/market_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Tickers
    # BTC-USD: Bitcoin
    # CL=F: Crude Oil Futures
    # GC=F: Gold Futures
    # ^TNX: 10-Year Treasury Yield (Proxy for Rates/FED)
    tickers = {
        "BTC": "BTC-USD",
        "OIL": "CL=F",
        "GOLD": "GC=F",
        "FED": "^TNX" 
    }
    
    print("📉 Fetching Market Data (2015-2025)...")
    
    for asset, ticker in tickers.items():
        try:
            print(f"   Fetching {asset} ({ticker})...")
            df = yf.download(ticker, start="2015-01-01", end="2025-12-31", progress=False)
            
            # Reset index to make Date a column
            df.reset_index(inplace=True)
            
            # Standardize columns (yfinance structure can vary)
            # Flatten MultiIndex if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Ensure Date format
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            
            # Calculate Daily Change & Volatility
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            df['Change_Pct'] = df['Close'].pct_change() * 100
            
            # Save
            filename = f"{output_dir}/{asset}_price_history.csv"
            df.to_csv(filename, index=False)
            print(f"   ✅ Saved {asset} to {filename}")
            
        except Exception as e:
            print(f"   ❌ Error fetching {asset}: {e}")

if __name__ == "__main__":
    fetch_market_history()
