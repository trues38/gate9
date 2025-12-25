import pandas as pd
import os

TREASURY_PATH = "processed/rdata_treasury.csv"
FEATURES_2025_PATH = "processed/features_2025.csv"
OUTPUT_PATH = "processed/rdata_unified.csv"

def unite_data():
    print("🚀 Unifying History and 2025 Data...")
    
    # 1. Load History
    if not os.path.exists(TREASURY_PATH):
        print("❌ History Missing")
        return
    df_hist = pd.read_csv(TREASURY_PATH, header=0) # We confirmed header=0
    print(f"   📜 History: {len(df_hist)} rows")
    
    # 2. Load 2025
    if not os.path.exists(FEATURES_2025_PATH):
        print("❌ 2025 Data Missing")
        return
    df_curr = pd.read_csv(FEATURES_2025_PATH)
    print(f"   🆕 2025 Data: {len(df_curr)} rows")
    
    # 3. Align Columns
    # Intersection of columns
    common_cols = list(set(df_hist.columns) & set(df_curr.columns))
    print(f"   🔗 Common Columns: {len(common_cols)}")
    
    # Check for critical missing cols in History that might be in 2025 (e.g. NetRtg_Sea proxy)
    # df_hist might lack 'NetRtg_Sea' if it wasn't in original dump?
    # User said "Schema Synchronization" was to match Treasury.
    # So Treasury HAS avg_V_4 etc.
    # But does Treasury have 'NetRtg_Sea'? Probably not if I added it as a Proxy.
    # If I want Uniformity, I should stick to the RAW Rolling columns for clustering.
    # 'NetRtg_Sea' is an Engine Artifact.
    # So we only keep common rolling columns.
    
    df_combined = pd.concat([df_hist[common_cols], df_curr[common_cols]])
    
    # 4. Dedup (In case 2025 data overlaps with Treasury backup?)
    # Generally assume Treasury ends where 2025 begins.
    # But safer to drop duplicates on Date+Team.
    df_combined['Date'] = pd.to_datetime(df_combined['Date'])
    df_combined = df_combined.sort_values('Date', ascending=False).drop_duplicates(subset=['Date', 'Team'])
    df_combined = df_combined.sort_values(['Team', 'Date'])
    
    # 5. Save
    df_combined.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Unified Dataset Created: {OUTPUT_PATH}")
    print(f"   Total Rows: {len(df_combined)}")
    print(f"   Date Range: {df_combined['Date'].min()} to {df_combined['Date'].max()}")

if __name__ == "__main__":
    unite_data()
