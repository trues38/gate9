import pandas as pd
import numpy as np
import os

GAP_PATH = "processed/odds_2025.csv"
TREASURY_PATH = "processed/rdata_treasury.csv"

def merge_gap_to_treasury():
    print(f"🚀 Starting Merge: {GAP_PATH} -> {TREASURY_PATH}")
    
    # 1. Load Data
    if not os.path.exists(GAP_PATH):
        print(f"❌ Gap file not found: {GAP_PATH}")
        return
        
    df_gap = pd.read_csv(GAP_PATH)
    print(f"   Loaded Gap Data: {len(df_gap)} rows")
    
    df_treasury = pd.read_csv(TREASURY_PATH)
    print(f"   Loaded Treasury: {len(df_treasury)} rows")
    
    # 2. Transform Gap Data to Raw Schema
    records = []
    
    # We need to map 'odds_2025' cols to 'rdata_treasury' core cols.
    # Core Cols needed for Feature Builder: Date, Team, Opponent, Points, OpponentPoints, odds, Location (implied by Team/Opp order usually)
    # Treasury has `local` column (Home/Away indicator? 'Home'/'Away' string or boolean?) checks...
    # Treasury header shows: `local` column.
    
    for idx, row in df_gap.iterrows():
        # Clean Inputs
        h_team = str(row['Home']).strip()
        a_team = str(row['Away']).strip()
        date_str = str(row['Date']).strip()
        
        # Parse Odds
        h_odds = row.get('H_Odds', 1.91)
        a_odds = row.get('A_Odds', 1.91)
        
        # Parse Scores
        h_score = row['H_Score']
        a_score = row['A_Score']
        
        # --- Home Record ---
        # Note: Treasury usually has `local` as 'Home' or 'Away' (from features).
        # But wait, original Treasury might have different schema.
        # Let's verify `local` format in Treasury sample.
        # Assuming it matches what build_features produces: 'Home'/'Away'.
        
        records.append({
            'Date': date_str,
            'Team': h_team,
            'Opponent': a_team,
            'Points': h_score,
            'OpponentPoints': a_score,
            'odds': h_odds,
            'local': 'Home' 
        })
        
        # --- Away Record ---
        records.append({
            'Date': date_str,
            'Team': a_team,
            'Opponent': h_team,
            'Points': a_score,
            'OpponentPoints': h_score,
            'odds': a_odds,
            'local': 'Away'
        })
        
    df_new = pd.DataFrame(records)
    df_new['Date'] = pd.to_datetime(df_new['Date']) # Enforce type
    
    # 3. Append to Treasury
    # We need to align columns. Treasury has many engineering columns.
    # We will just append the common ones, leaving others NaN.
    # The build_features pipeline re-calculates rolling stats anyway.
    
    # Enforce Treasury Date type for comparison
    df_treasury['Date'] = pd.to_datetime(df_treasury['Date'])
    
    # Concat
    # Filter out duplicates based on Date + Team
    # We assume Treasury is the base. We only add NEW rows from Gap.
    
    # Create key for existence check
    existing_keys = set(zip(df_treasury['Date'], df_treasury['Team']))
    
    new_rows = []
    for idx, row in df_new.iterrows():
        key = (row['Date'], row['Team'])
        if key not in existing_keys:
            new_rows.append(row)
            
    if not new_rows:
        print("⚠️ No new rows to add. All Gap data already in Treasury?")
    else:
        df_to_add = pd.DataFrame(new_rows)
        print(f"   ✨ Adding {len(df_to_add)} new rows to Treasury.")
        
        # Align columns - fill missing with NaN
        # We concat, pandas handles missing cols by filling NaN
        df_updated = pd.concat([df_treasury, df_to_add], ignore_index=True)
        
        # Sort
        df_updated = df_updated.sort_values(['Date', 'Team'])
        
        # Save
        df_updated.to_csv(TREASURY_PATH, index=False)
        print(f"✅ Saved Updated Treasury: {len(df_updated)} rows")

if __name__ == "__main__":
    merge_gap_to_treasury()
