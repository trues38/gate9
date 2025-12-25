import pandas as pd

DIRTY_PATH = "processed/rdata_treasury_dirty.csv"

def audit_deleted():
    print(f"🔍 Analyzing Deleted Rows from {DIRTY_PATH}...")
    try:
        df = pd.read_csv(DIRTY_PATH)
    except FileNotFoundError:
        print("❌ Dirty Backup not found. Cannot audit.")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    
    # 1. Inspect Duplicates
    dup_mask = df.duplicated(subset=['Date', 'Team'], keep=False)
    duplicates = df[dup_mask].sort_values(['Date', 'Team'])
    
    print(f"\n[1] DUPLICATES FOUND: {len(duplicates)} rows")
    if not duplicates.empty:
        print(duplicates[['Date', 'Team', 'Opponent']].head(10).to_string(index=False))
        
    # 2. Inspect Orphans
    # Orphans are rows where (Date, Team) exists but (Date, Opponent) does NOT.
    
    # Create Set of ALL (Date, Team) keys
    valid_keys = set(zip(df['Date'], df['Team']))
    
    orphans = []
    
    for idx, row in df.iterrows():
        # Check if the OTHER SIDE exists
        opp_key = (row['Date'], row['Opponent'])
        if opp_key not in valid_keys:
            orphans.append(row)
            
    orphans_df = pd.DataFrame(orphans)
    
    print(f"\n[2] ORPHANS FOUND (Missing Opponent Record): {len(orphans_df)} rows")
    if not orphans_df.empty:
        # Sort by Date
        orphans_df = orphans_df.sort_values('Date')
        
        print("\n--- SAMPLE OF DELETED ORPHANS ---")
        print(orphans_df[['Date', 'Team', 'Opponent', 'Points', 'OpponentPoints']].head(15).to_string(index=False))
        
        print("\n--- ANALYSIS ---")
        # Check if these are recent or ancient
        years = orphans_df['Date'].dt.year.value_counts().sort_index()
        print(f"Orphans by Year:\n{years}")

if __name__ == "__main__":
    audit_deleted()
