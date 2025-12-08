import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client

class BacktestEngine:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.market_ticker = "SPY" # Default Market Proxy

    def run_backtest(self, start_date: str, end_date: str):
        print(f"📉 Starting Backtest Engine ({start_date} ~ {end_date})...")
        
        # 1. Fetch Macro Data (Signals)
        macro_data = self._fetch_macro_data(start_date, end_date)
        if not macro_data:
            print("   ⚠️ No macro data found.")
            return

        # 2. Fetch Price Data (Returns)
        price_data = self._fetch_price_data(start_date, end_date, self.market_ticker)
        if not price_data:
            print("   ⚠️ No price data found.")
            return
            
        # Convert to DataFrame for easy calc
        df_macro = pd.DataFrame(macro_data)
        df_price = pd.DataFrame(price_data)
        
        # Merge on date
        df = pd.merge(df_macro, df_price, on='date', how='inner')
        
        # Calculate Forward Returns
        # We need future prices. Since we fetched a range, we might miss the 'future' for the last few days.
        # Ideally we fetch price data slightly beyond end_date.
        # For simplicity in this batch script, we assume the price_data covers enough.
        # But to be robust, let's fetch extra price data.
        
        # Re-fetch price with buffer
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        buffer_date = (end_dt + timedelta(days=10)).strftime("%Y-%m-%d")
        price_data_extended = self._fetch_price_data(start_date, buffer_date, self.market_ticker)
        df_price = pd.DataFrame(price_data_extended)
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_price = df_price.sort_values('date')
        
        # Calculate Returns
        df_price['ret_1d'] = df_price['close'].pct_change(periods=1).shift(-1) # Next day return
        df_price['ret_5d'] = df_price['close'].pct_change(periods=5).shift(-5) # Next 5 days return
        
        # Merge back
        df_macro['date'] = pd.to_datetime(df_macro['date'])
        merged = pd.merge(df_macro, df_price[['date', 'ret_1d', 'ret_5d', 'close']], on='date', how='left')
        
        results = []
        for _, row in merged.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            z_score = row.get('zscore', 0.0)
            
            # Define Signals (Strategy: Z_SCORE_BASIC_V1)
            # 1. Z-Score Extremes
            signal_type = "NEUTRAL"
            if z_score > 1.5: signal_type = "Z_SCORE_HIGH"
            elif z_score < -1.5: signal_type = "Z_SCORE_LOW"
            
            if signal_type != "NEUTRAL":
                results.append({
                    "date": date_str,
                    "ticker": self.market_ticker,
                    "strategy_id": "Z_SCORE_BASIC_V1", # Versioned Strategy ID
                    "signal_type": signal_type,
                    "signal_value": z_score,
                    "fwd_return_1d": row['ret_1d'],
                    "fwd_return_5d": row['ret_5d'],
                    "is_valid_signal": True,
                    "metadata": json.dumps({"threshold": 1.5}), # Parameter Metadata
                    "created_at": "now()"
                })
                
        # 3. Save Results
        if results:
            self._save_results(results)
            print(f"✅ Backtest Complete. Saved {len(results)} signals.")
        else:
            print("   ℹ️ No significant signals found.")

    def _fetch_macro_data(self, start_date, end_date):
        try:
            # Fetch US data for backtest (assuming SPY backtest)
            res = self.supabase.table("preprocess_daily")\
                .select("date, zscore, headline_count")\
                .eq("country", "US")\
                .gte("date", start_date)\
                .lte("date", end_date)\
                .execute()
            return res.data
        except Exception as e:
            print(f"Error fetching macro data: {e}")
            return []

    def _fetch_price_data(self, start_date, end_date, ticker):
        try:
            res = self.supabase.table("ingest_prices")\
                .select("date, close")\
                .eq("ticker", ticker)\
                .gte("date", start_date)\
                .lte("date", end_date)\
                .execute()
            return res.data
        except Exception as e:
            print(f"Error fetching price data: {e}")
            return []

    def _save_results(self, results):
        try:
            # Batch insert
            batch_size = 100
            for i in range(0, len(results), batch_size):
                batch = results[i:i+batch_size]
                # Handle NaN for JSON
                cleaned_batch = []
                for item in batch:
                    if pd.isna(item['fwd_return_1d']): item['fwd_return_1d'] = None
                    if pd.isna(item['fwd_return_5d']): item['fwd_return_5d'] = None
                    cleaned_batch.append(item)
                    
                self.supabase.table("backtest_log").upsert(cleaned_batch, on_conflict="date, ticker, strategy_id").execute()
        except Exception as e:
            print(f"Error saving backtest results: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default="2025-12-31")
    args = parser.parse_args()
    
    engine = BacktestEngine()
    engine.run_backtest(args.start, args.end)
