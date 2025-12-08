import os
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# Factor-7 Ticker Map
TICKERS = {
    "rates": "^TNX",
    "dollar": "DX-Y.NYB",
    "oil": "CL=F",
    "gold": "GC=F",
    "risk_vix": "^VIX", # If available, else use proxy
    "kr_market": "^KS11",
    "jp_market": "^N225",
    "cn_market": "000001.SS",
    "us_market": "SPY"
}

def fetch_price_history(ticker, end_date, days=365):
    """Fetch price history for Z-Score calculation."""
    try:
        # We need enough history for rolling Z-score (e.g. 1 year)
        # Fetch from ingest_prices
        # Note: ingest_prices has 'date' column.
        
        # Calculate start date
        end_dt = pd.to_datetime(end_date)
        start_dt = end_dt - timedelta(days=days + 30) # Buffer
        
        response = supabase.table("ingest_prices")\
            .select("date, close")\
            .eq("ticker", ticker)\
            .lte("date", end_date)\
            .gte("date", start_dt.strftime("%Y-%m-%d"))\
            .order("date", desc=True)\
            .execute()
            
        df = pd.DataFrame(response.data)
        if df.empty:
            return None
            
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        return df.set_index('date')
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def calculate_zscore(current_val, history_series, window=252):
    if len(history_series) < 30:
        return 0.0
    
    # Rolling window stats
    # We want the z-score of the current value relative to the past window
    rolling_mean = history_series.rolling(window=window).mean().iloc[-1]
    rolling_std = history_series.rolling(window=window).std().iloc[-1]
    
    if rolling_std == 0 or np.isnan(rolling_std):
        return 0.0
        
    return (current_val - rolling_mean) / rolling_std

def determine_trend(z_score, delta_z):
    """Determine trend label based on Z-Score and its change."""
    if z_score > 2.0:
        return "Spike (Extreme)"
    elif z_score < -2.0:
        return "Crash (Extreme)"
    elif z_score > 1.0 and delta_z > 0.1:
        return "Rising Fast"
    elif z_score < -1.0 and delta_z < -0.1:
        return "Falling Fast"
    elif z_score > 0.5:
        return "Uptrend"
    elif z_score < -0.5:
        return "Downtrend"
    else:
        return "Neutral"

def run_factor_engine(target_date):
    print(f"🧠 [Factor-7] Calculating Factors for {target_date}...")
    
    factors = {}
    raw_changes = {}
    
    # 1. Fetch Data for all tickers
    data_cache = {}
    for key, ticker in TICKERS.items():
        df = fetch_price_history(ticker, target_date)
        data_cache[key] = df
        
    # 2. Calculate Factors
    
    # --- Factor 1: Rates (TNX) ---
    df = data_cache.get("rates")
    if df is not None and not df.empty:
        curr = df['close'].iloc[-1]
        z = calculate_zscore(curr, df['close'])
        # Delta Z (change from yesterday)
        prev_z = calculate_zscore(df['close'].iloc[-2], df['close'].iloc[:-1]) if len(df) > 1 else z
        delta_z = z - prev_z
        factors["rates"] = {
            "state": determine_trend(z, delta_z),
            "zscore": round(z, 2),
            "value": curr
        }
        raw_changes["rates_delta"] = delta_z
    else:
        factors["rates"] = {"state": "Unknown", "zscore": 0, "value": 0}

    # --- Factor 2: Dollar (DXY) ---
    df = data_cache.get("dollar")
    if df is not None and not df.empty:
        curr = df['close'].iloc[-1]
        z = calculate_zscore(curr, df['close'])
        prev_z = calculate_zscore(df['close'].iloc[-2], df['close'].iloc[:-1]) if len(df) > 1 else z
        delta_z = z - prev_z
        factors["dollar"] = {
            "state": determine_trend(z, delta_z),
            "zscore": round(z, 2),
            "value": curr
        }
    else:
        factors["dollar"] = {"state": "Unknown", "zscore": 0}

    # --- Factor 3: Inflation (Oil + Gold Proxy) ---
    # Simplified: If Oil & Gold both up -> Inflationary
    oil_df = data_cache.get("oil")
    gold_df = data_cache.get("gold")
    
    oil_z = 0
    if oil_df is not None and not oil_df.empty:
        oil_z = calculate_zscore(oil_df['close'].iloc[-1], oil_df['close'])
        
    factors["inflation"] = {
        "state": "Heating Up" if oil_z > 1.0 else "Cooling" if oil_z < -1.0 else "Stable",
        "oil_z": round(oil_z, 2)
    }
    factors["commodities"] = {
        "state": determine_trend(oil_z, 0), # Simplified
        "oil_z": round(oil_z, 2)
    }

    # --- Factor 6: Risk Sentiment (VIX or Market Drop) ---
    # If VIX missing, use SPY drop
    vix_df = data_cache.get("risk_vix")
    spy_df = data_cache.get("us_market")
    
    risk_state = "Neutral"
    risk_z = 0
    
    if vix_df is not None and not vix_df.empty:
        risk_z = calculate_zscore(vix_df['close'].iloc[-1], vix_df['close'])
        if risk_z > 1.5: risk_state = "Risk-Off (Fear)"
        elif risk_z < -1.0: risk_state = "Risk-On (Greed)"
    elif spy_df is not None and not spy_df.empty:
        # Proxy: SPY crashing = Risk Off
        spy_z = calculate_zscore(spy_df['close'].iloc[-1], spy_df['close'])
        if spy_z < -1.5: risk_state = "Risk-Off (Fear)"
        elif spy_z > 1.0: risk_state = "Risk-On (Greed)"
        risk_z = -spy_z # Invert for risk metric
        
    factors["risk"] = {
        "state": risk_state,
        "zscore": round(risk_z, 2)
    }

    # --- Factor 7: Region (CN vs KR) ---
    cn_df = data_cache.get("cn_market")
    kr_df = data_cache.get("kr_market")
    
    region_state = "Synced"
    if cn_df is not None and kr_df is not None and not cn_df.empty and not kr_df.empty:
        cn_z = calculate_zscore(cn_df['close'].iloc[-1], cn_df['close'])
        kr_z = calculate_zscore(kr_df['close'].iloc[-1], kr_df['close'])
        
        if cn_z > 1.0 and kr_z < -0.5:
            region_state = "CN Outperforming"
        elif kr_z > 1.0 and cn_z < -0.5:
            region_state = "KR Outperforming"
            
    factors["region"] = {
        "state": region_state
    }
    
    # Fill others with defaults for now
    factors["liquidity"] = {"state": "Neutral (Default)"}

    # Output
    result = {
        "date": target_date,
        "factors": factors,
        "raw_changes": raw_changes
    }
    
    print(f"✅ Factors Calculated: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    # Test run
    run_factor_engine("2024-01-05")
