import pandas as pd
import os

RDATA_PATH = "processed/rdata_treasury.csv"
BACKUP_PATH = "processed/rdata_treasury_dirty.csv"

def fix_data():
    print("🧹 Starting Data Cleaning...")
    df = pd.read_csv(RDATA_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # 0. Backup
    df.to_csv(BACKUP_PATH, index=False)
    print(f"📦 Backup saved to {BACKUP_PATH} ({len(df)} rows)")
    
    # 1. Drop Exact Duplicates (Date, Team)
    print("1️⃣  Dropping Duplicates...")
    initial_count = len(df)
    
    # Sort by date to keep 'last' or 'first'? likely first is fine if identical.
    # If different, we might have issues. Assuming duplicates are identical log entries.
    df = df.drop_duplicates(subset=['Date', 'Team'], keep='first')
    
    dedup_count = len(df)
    print(f"   Removed {initial_count - dedup_count} duplicates.")
    
    # 2. Fix Orphans (Mirror Check)
    print("2️⃣  Checking Mirror Integrity (Orphans)...")
    # We need to ensure that if Home(A) vs Away(B) exists, Away(B) vs Home(A) also exists.
    # Strategy: Create a Set of (Date, Team).
    # Iterate through rows. Construct 'Opponent' Key. Check if in Set.
    
    # Efficient way:
    # Key = (Date, Team)
    # OppKey = (Date, Opponent)
    
    keys = set(zip(df['Date'], df['Team']))
    
    valid_indices = []
    orphans = 0
    
    for idx, row in df.iterrows():
        opp_key = (row['Date'], row['Opponent'])
        if opp_key in keys:
            valid_indices.append(idx)
        else:
            orphans += 1
            # print(f"   Found Orphan: {row['Date'].date()} {row['Team']} vs {row['Opponent']}")
            
    if orphans > 0:
        print(f"   Found {orphans} Orphans. Removing them to ensure symmetry.")
        df = df.loc[valid_indices]
    else:
        print("   No Orphans found. Data is symmetric.")
        
    # 3. Sort and Save
    df = df.sort_values(['Team', 'Date'])
    df.to_csv(RDATA_PATH, index=False)
    
    print(f"\n✅ Data Cleaned and Saved.")
    print(f"   Old Count: {initial_count}")
    print(f"   New Count: {len(df)}")
    print(f"   Removed Total: {initial_count - len(df)}")

if __name__ == "__main__":
    fix_data()
