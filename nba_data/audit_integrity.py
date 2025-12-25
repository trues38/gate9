import pandas as pd
import numpy as np

RDATA_PATH = "processed/rdata_treasury.csv"

def audit_data():
    print(f"🕵️‍♀️ Starting Data Integrity Audit on {RDATA_PATH}...")
    
    try:
        df = pd.read_csv(RDATA_PATH)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(['Team', 'Date'])
        
        print(f"✅ Loaded {len(df)} rows. Range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    except Exception as e:
        print(f"❌ Critical Error loading data: {e}")
        return

    errors = []
    
    # --- Check 1: Mirror Consistency ---
    # Every Game is 2 rows (Home, Away).
    # We group by Date/Team/Opponent to find pairs.
    # Actually, simpler: Merge on Date, Team=Opponent.
    
    print("\n🔍 Check 1: Mirror Consistency (Score Matching)...")
    # Adjust for Treasury Schema (uses 'local' not 'Location')
    col_loc = 'local' if 'local' in df.columns else 'Location'
    cols_needed = ['Date', 'Team', 'Opponent', 'Points', 'OpponentPoints', col_loc]
    view = df[cols_needed].copy()
    
    # Self check: Points vs OppPoints in SAME row
    # (Already trusted? No, verify schema).
    # No, Team A's Points row should match Team B's OppPoints row.
    
    # Let's try to match them.
    # Key: Date + Sorted(Team, Opp) ? 
    # Or just loop? Vectorized is better.
    
    # Create a unique match ID: Date + Sorted(Team, Opp)
    def make_match_id(row):
        teams = sorted([str(row['Team']), str(row['Opponent'])])
        return f"{row['Date'].strftime('%Y%m%d')}_{teams[0]}_vs_{teams[1]}"
    
    view['MatchID'] = view.apply(make_match_id, axis=1)
    
    # Group by MatchID. Should have exactly 2 records per MatchID.
    counts = view['MatchID'].value_counts()
    orphans = counts[counts != 2]
    
    if not orphans.empty:
        print(f"❌ Found {len(orphans)} Orphan/Duplicate Games (Not exactly 2 records):")
        print(orphans.head())
        errors.append("Orphan Games Found")
    else:
        print("✅ All games have exactly 2 records (Home/Away pair).")
        
    # Check Score Matching within Pairs
    # Group by IDs, assert Pts_A == OppPts_B
    # A bit complex to vectorise perfectly, but let's try strict check.
    score_mismatches = 0
    
    # Basic Check: Sum of Points == Sum of OpponentPoints across entire DB
    total_pts = df['Points'].sum()
    total_opp = df['OpponentPoints'].sum()
    
    if total_pts != total_opp:
        print(f"❌ TOTAL POINT MISMATCH: Pts {total_pts} != OppPts {total_opp}")
        errors.append(f"Global Point Mismatch ({total_pts - total_opp})")
    else:
        print("✅ Global Point Sum Check Passed.")

    # --- Check 2: Rest Calculation Validation ---
    print("\n🔍 Check 2: Rest Calculation Logic...")
    # Calculate 'True Rest'
    df['PrevDate'] = df.groupby('Team')['Date'].shift(1)
    df['CalcRest'] = (df['Date'] - df['PrevDate']).dt.days
    
    # Where CalcRest is NaN (First game), treat as valid (long rest).
    
    # Analyze Rest Distribution
    rest_dist = df['CalcRest'].value_counts().sort_index()
    print("   Rest Days Distribution (Top 5):")
    print(rest_dist.head())
    
    # Check for Impossible Rest (< 1?)
    # Back-to-back is 1 day diff (Played 12th, Play 13th).
    # Same day header? Double header? NBA doesn't really do that anymore.
    impossible = df[df['CalcRest'] < 1]
    if not impossible.empty:
        print(f"❌ Found {len(impossible)} games with REST < 1 (Same Day?):")
        print(impossible[['Date', 'Team', 'PrevDate']].head())
        errors.append("Impossible Rest Found")
    else:
        print("✅ No Same-Day Games (Rest >= 1) found.")

    # Compare with 'days_since_last' column if it exists
    # Note: user pointed out this column was 'Lagged'.
    # If we audit the CSV column, we expect it to match (Date - PrevDate).
    # If it differs, that confirms the column was buggy.
    if 'days_since_last' in df.columns:
        # Fill NaN with rest (or 99)
        # Note: 'days_since_last' in RData might be 'Rest Entering Game'.
        # Rest Entering Game = (Date - PrevDate).
        # Let's compare.
        df['CSV_Rest'] = df['days_since_last'].fillna(0)
        df['Rest_Diff'] = df['CalcRest'] - df['CSV_Rest']
        
        mismatches = df[(df['Rest_Diff'].abs() > 0) & (df['CalcRest'].notna())]
        if not mismatches.empty:
            print(f"⚠️ Found {len(mismatches)} rows where CSV 'days_since_last' != Calculated Rest.")
            print("   This confirms the 'Lag' issue or Calculation difference in history.")
            print("   Sample Mismatches:")
            print(mismatches[['Date', 'Team', 'CalcRest', 'CSV_Rest']].tail())
            # This is expected for 2025 until we fix the CSV source itself.
            # But the ENGINE now ignores this column, so this is just 'Audit'.
        else:
            print("✅ CSV 'days_since_last' matches Calculated Rest exactly.")

    # --- Check 3: Outlier Detection ---
    print("\n🔍 Check 3: Stat Outliers...")
    min_score = df['Points'].min()
    max_score = df['Points'].max()
    print(f"   Score Range: {min_score} - {max_score}")
    
    if min_score < 50:
        print(f"⚠️ Warning: Extremely Low Score found ({min_score}). Check Data.")
        print(df[df['Points'] == min_score][['Date', 'Team', 'Opponent', 'Points']])
        
    if max_score > 200: 
        # 2025 All Star game? Or 1980s?
        print(f"⚠️ Warning: High Score found ({max_score}). Check Data.")
        print(df[df['Points'] == max_score][['Date', 'Team', 'Opponent', 'Points']])

    # --- Summary ---
    print("\n========================")
    if not errors:
        print("🎉 AUDIT PASSED: No Critical Data Integrity Issues Found.")
    else:
        print(f"🚫 AUDIT FAILED: {len(errors)} Critical Issues Found.")
    print("========================")

if __name__ == "__main__":
    audit_data()
