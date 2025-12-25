import pyreadr
import pandas as pd
import os

R_FILE = "kaggle_data/NBA_games_info.RData"
OUT_CSV = "processed/rdata_treasury.csv"

print(f"🚀 [Ingest] Loading {R_FILE}...")

try:
    # 1. Load RData
    result = pyreadr.read_r(R_FILE)
    
    # RData can contain multiple objects. We usually want the first one or the biggest one.
    keys = list(result.keys())
    print(f"📦 Objects found in RData: {keys}")
    
    # We assume the main dataframe is the first one or named 'NBA_games_info'
    df = result[keys[0]]
    
    print(f"✅ Loaded DataFrame: {df.shape}")
    
    # 2. Inspect Columns (Treasure Hunt)
    target_cols = ['avg_V_4', 'days_since_last', 'score_last_10_between', 'n_victorias']
    found_cols = [c for c in target_cols if c in df.columns]
    
    print("\n🔍 Treasure Scan:")
    for c in target_cols:
        status = "✅ Found" if c in df.columns else "❌ Missing"
        print(f"   - {c}: {status}")
        
    # 3. Save as CSV for easy access by other engines
    os.makedirs("processed", exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n💾 Saved converted treasury to: {OUT_CSV}")
    
    # 4. Show sample
    print("\n📊 Column Check:")
    print(df.columns.tolist())
    print("\n📊 Sample Row:")
    print(df.iloc[0].to_dict())

except Exception as e:
    print(f"🚨 Error processing RData: {e}")
