import pandas as pd
import os

DATA_DIR = "regime_zero/data/multi_asset_history"

def load_btc_history():
    """Loads Bitcoin historical data."""
    path = f"{DATA_DIR}/btc_history.csv"
    if not os.path.exists(path):
        print(f"⚠️ BTC History not found at {path}")
        return None
    return pd.read_csv(path)

def load_fed_history():
    """Loads Fed Rate / Monetary Policy history."""
    path = f"{DATA_DIR}/fed_history.csv"
    if not os.path.exists(path):
        print(f"⚠️ Fed History not found at {path}")
        return None
    return pd.read_csv(path)

def load_oil_history():
    """Loads Crude Oil (CL=F) history."""
    path = f"{DATA_DIR}/oil_history.csv"
    if not os.path.exists(path):
        print(f"⚠️ Oil History not found at {path}")
        return None
    return pd.read_csv(path)

def load_gold_history():
    """Loads Gold (GC=F) history."""
    path = f"{DATA_DIR}/gold_history.csv"
    if not os.path.exists(path):
        print(f"⚠️ Gold History not found at {path}")
        return None
    return pd.read_csv(path)

def load_all_histories():
    """Loads all available historical data."""
    return {
        "BTC": load_btc_history(),
        "FED": load_fed_history(),
        "OIL": load_oil_history(),
        "GOLD": load_gold_history()
    }

if __name__ == "__main__":
    print("🔍 Checking for Multi-Asset Data...")
    data = load_all_histories()
    for key, df in data.items():
        status = "✅ Loaded" if df is not None else "❌ Missing"
        print(f"{key}: {status}")
