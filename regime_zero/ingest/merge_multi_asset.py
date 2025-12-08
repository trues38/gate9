import pandas as pd
import os
import glob

# Configuration
DATA_DIR = "regime_zero/data/multi_asset_history"
OUTPUT_FILE = f"{DATA_DIR}/unified_history.csv"

def load_and_label(pattern, asset_class):
    files = glob.glob(f"{DATA_DIR}/{pattern}")
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            # Ensure columns exist
            if 'published' not in df.columns:
                print(f"⚠️ Skipping {f}: Missing 'published' column")
                continue
                
            # Normalize Date
            # Some might be YYYY-MM-DD, others might need parsing
            df['date'] = pd.to_datetime(df['published'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Add Asset Class
            df['asset_class'] = asset_class
            
            # Select relevant columns
            cols = ['date', 'title', 'source', 'link', 'asset_class']
            # Handle missing columns gracefully
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            
            dfs.append(df[cols])
            print(f"✅ Loaded {len(df)} rows from {os.path.basename(f)} ({asset_class})")
            
            if asset_class == "GOLD":
                 print(f"DEBUG GOLD HEAD:\n{df[cols].head()}")
                 print(f"DEBUG GOLD DATES:\n{df['date'].head()}")
        except Exception as e:
            print(f"❌ Error loading {f}: {e}")
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def merge_datasets():
    print("🚀 Starting Multi-Asset Merge...")
    
    # 1. BTC
    btc_df = load_and_label("btc_news*.csv", "BTC")
    
    # 2. FED
    fed_df = load_and_label("fed_news*.csv", "FED")
    
    # 3. OIL
    oil_df = load_and_label("oil_news*.csv", "OIL")
    
    # 4. GOLD
    gold_df = load_and_label("gold_news*.csv", "GOLD")
    
    # Combine All
    all_df = pd.concat([btc_df, fed_df, oil_df, gold_df], ignore_index=True)
    
    # Drop Invalid Dates
    all_df = all_df.dropna(subset=['date'])
    all_df = all_df[all_df['date'] != "NaT"]
    
    # Sort by Date (Descending)
    all_df = all_df.sort_values(by='date', ascending=False)
    
    # Deduplicate (Title + Date)
    before_len = len(all_df)
    all_df.drop_duplicates(subset=['title', 'date'], inplace=True)
    after_len = len(all_df)
    print(f"🧹 Deduplicated: {before_len} -> {after_len} (Removed {before_len - after_len})")
    
    # Save
    all_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n💾 Unified History Saved: {OUTPUT_FILE}")
    print(f"📊 Total Records: {len(all_df)}")
    print(all_df['asset_class'].value_counts())

if __name__ == "__main__":
    merge_datasets()
