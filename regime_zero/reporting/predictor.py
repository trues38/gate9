import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.ingest.fetch_market_data import fetch_price_history

def calculate_regime_stats(regime_dates, ticker="SPY"):
    """
    Calculates forward returns for the regime episodes.
    """
    print(f"🔮 [Regime Zero] Calculating Stats for {len(regime_dates)} episodes...")
    
    returns_4w = []
    returns_8w = []
    
    for date_str in regime_dates:
        # Fetch price history around this date
        # We need future data relative to the regime date
        # Check if date is too recent
        date_dt = pd.to_datetime(date_str)
        if date_dt > datetime.now() - timedelta(days=30):
            # Too recent to know 4w return
            continue
            
        # Fetch 60 days of future data
        # We use fetch_price_history but we need to trick it or use a different query
        # fetch_price_history gets *past* data.
        # We need a new function or just fetch a large range.
        # For simplicity, let's assume we can't easily get future data with existing function 
        # without modifying it to accept start_date/end_date range explicitly.
        # But fetch_price_history takes 'end_date' and looks back.
        # So to get future of date X, we can call fetch_price_history(end_date=X+60days, days=60).
        
        future_end = date_dt + timedelta(days=60)
        df = fetch_price_history(ticker, future_end.strftime("%Y-%m-%d"), days=60)
        
        if df is not None and not df.empty:
            try:
                # Find price at date X
                # df is indexed by date
                # We need exact date or closest forward
                # df is sorted by date
                
                # Get price at regime date
                # We need to find the index closest to date_dt
                # Since df contains [date_dt, future_end], we look for date_dt
                
                # Filter for >= date_dt
                future_df = df[df.index >= date_dt]
                if future_df.empty:
                    continue
                    
                start_price = future_df.iloc[0]['close']
                
                # 4 weeks later (20 trading days)
                # Check if we have enough data
                if len(future_df) > 20:
                    price_4w = future_df.iloc[20]['close']
                    ret_4w = (price_4w - start_price) / start_price
                    returns_4w.append(ret_4w)
                    
                # 8 weeks later (40 trading days)
                if len(future_df) > 40:
                    price_8w = future_df.iloc[40]['close']
                    ret_8w = (price_8w - start_price) / start_price
                    returns_8w.append(ret_8w)
            except Exception as e:
                print(f"Error calc stats for {date_str}: {e}")
                
    stats = {
        "count": len(returns_4w),
        "avg_4w": np.mean(returns_4w) if returns_4w else 0.0,
        "avg_8w": np.mean(returns_8w) if returns_8w else 0.0,
        "win_rate_4w": sum(r > 0 for r in returns_4w) / len(returns_4w) if returns_4w else 0.0,
        "best_4w": np.max(returns_4w) if returns_4w else 0.0,
        "worst_4w": np.min(returns_4w) if returns_4w else 0.0
    }
    
    return stats

if __name__ == "__main__":
    # Test
    stats = calculate_regime_stats(["2024-01-01", "2024-02-01"])
    print(stats)
