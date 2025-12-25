import duckdb
import pandas as pd
import numpy as np
import os
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

OUTPUT_PATH = "processed/features_2025.csv"

def get_rdata_treasury():
    """Load RData from exported CSV (Treasury)"""
    path = "processed/rdata_treasury.csv"
    if not os.path.exists(path):
        print("❌ Critical: RData Treasury Missing")
        return pd.DataFrame()
        
    print(f"📥 Loading RData Treasury: {path}")
    try:
        # Load with header=0 (Confirmed)
        df = pd.read_csv(path, header=0)
        
        # Standardize necessary columns for merge
        needed_map = {
            'Date': 'Date', 'Team': 'Team', 'Points': 'Points', 
            'Opponent': 'Opponent', 'OpponentPoints': 'OpponentPoints',
            'local': 'Location' # 'local' in Spanish RData often means Location/Home? 
            # Actually user header showed 'local'. 
            # If 'local' is Home (1/0), we map it later.
        }
        
        # If headers match standard English:
        if 'H_Score' in df.columns: # Manual style
             pass 
        
        # Normalize to English for consistent internal logic, then map back to Spanish at end?
        # User wants "Same Columns as RData".
        # So output should use RData names: 'avg_V_4', etc.
        
        cols_keep = ['Date', 'Team', 'Points', 'Opponent', 'OpponentPoints']
        if 'odds' in df.columns: cols_keep.append('odds') # Capture Odds
        if 'local' in df.columns: cols_keep.append('local')
        if 'Home' in df.columns: cols_keep.append('Home')
        if 'game_id' in df.columns: cols_keep.append('game_id')
        
        df = df[cols_keep].copy()
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Filter 2025 - DISABLED (Need Full History for Rolling/Nemesis)
        # df = df[df['Date'] >= '2025-10-01'].copy()
        
        # Standardize for "Internal Calc"
        df['Location'] = 'Home' # Default? Need to verify.
        if 'local' in df.columns:
             df['Location'] = df['local'].apply(lambda x: 'Home' if str(x) in ['1', '1.0', 'Home'] else 'Away')
        elif 'Home' in df.columns:
             df['Location'] = df['Home'].apply(lambda x: 'Home' if x == 1 else 'Away')

        return df
    except Exception as e:
        print(f"⚠️ RData Load Failed: {e}")
        return pd.DataFrame()

# Gap Data Function Removed (Data Consolidated to Treasury)

def calculate_rolling(df):
    """Calculate RData-style rolling metrics"""
    # Keys
    # V = Win (1 if Pts > OppPts)
    # P = Points
    # P_o = OpponentPoints
    # Diff = P - P_o
    
    df['V'] = np.where(df['Points'] > df['OpponentPoints'], 1.0, 0.0)
    df['Diff'] = df['Points'] - df['OpponentPoints']
    
    # Sort
    df = df.sort_values(['Team', 'Date']).reset_index(drop=True)
    
    # Lag Stats (We predict based on PAST, so shift(1))
    
    windows = [1, 4, 8, 12, 16, 32]
    
    # Group by Team
    grouped = df.groupby('Team')
    
    # Metrics to roll
    # Structure: NewColName = (SourceCol, Window)
    
    for w in windows:
        # avg_V_X
        df[f'avg_V_{w}'] = grouped['V'].transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        # avg_P_X
        df[f'avg_P_{w}'] = grouped['Points'].transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        # avg_P_o_X
        df[f'avg_P_o_{w}'] = grouped['OpponentPoints'].transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        # avg_diff_P_X
        df[f'avg_diff_P_{w}'] = grouped['Diff'].transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())

    # Volatility (Std Dev of Margin) - Needed for Risk Score
    # Vol_Sea could be window 32 std
    df['Vol_Sea'] = grouped['Diff'].transform(lambda x: x.shift(1).rolling(32, min_periods=5).std())
    df['Vol_Sea'] = df['Vol_Sea'].fillna(10.0)

    # games_played
    df['games_played'] = grouped.cumcount()
    
    # days_since_last
    df['days_since_last'] = grouped['Date'].diff().dt.days.fillna(7) # Default 7 for first game
    
    # NetRtg_Sea (Season Net Rating) -> Proxy: Avg Margin L32 (Enough to cover season start)
    df['NetRtg_Sea'] = df['avg_diff_P_32']
    
    # Pace_Sea (Season Pace) -> (AvgPts + AvgOppPts) / 2
    df['Pace_Sea'] = (df['avg_P_32'] + df['avg_P_o_32']) / 2.0
    
    # NetRtg_L10 (Last 10 Games) -> Use L12 as close proxy or calc L10?
    # We calculated [1, 4, 8, 12, 16, 32].
    # Use L12 as L10 Proxy to avoid re-running loop for 10.
    # Or just use L8.
    df['NetRtg_L10'] = df['avg_diff_P_12']

    df['NetRtg_L10'] = df['avg_diff_P_12']

    return df

def calculate_matchup_metrics(df):
    """Calculates rolling avg points diff between specific teams."""
    print("⚔️ Calculating Historical Matchup Metrics (Nemesis Logic)...")
    
    # Logic: PlusMinus = Points - OpponentPoints
    # Then rolling mean of PlusMinus for each (Team, Opponent) pair
    
    # 1. Calc Score Diff
    df['ScoreDiff'] = df['Points'] - df['OpponentPoints']
    
    # 2. Group & Roll
    # Shift 1 to ensure we only use PAST games
    # min_periods=0 or 1? 1. If no history, it stays NaN (fill 0 later).
    
    # Helper to apply rolling
    def roll_matchup(g):
        # shift(1) excludes current game
        return g.shift(1).rolling(window=10, min_periods=1).mean()
        
    def roll_matchup_5(g):
        return g.shift(1).rolling(window=5, min_periods=1).mean()

    # Apply
    # Note: Sort is critical. df is already sorted by Team, Date.
    # Group by [Team, Opponent]
    
    # Performance Optimization: straightforward apply is slow?
    # 40k rows is fine for pandas group apply.
    
    grouped = df.groupby(['Team', 'Opponent'])['ScoreDiff']
    
    df['score_last_10_between'] = grouped.transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    df['score_last_5_between'] = grouped.transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    
    # Fill NaN with 0.0 (First meeting or no history)
    df['score_last_10_between'] = df['score_last_10_between'].fillna(0.0)
    df['score_last_5_between'] = df['score_last_5_between'].fillna(0.0)
    
    # Drop temp
    df = df.drop(columns=['ScoreDiff'])
    
    return df

def add_opponent_metrics(df):
    """Self-join to get avg_V_o_X (Opponent's Form)"""
    print("🔄 Adding Opponent Metrics...")
    
    # We want to pull 'avg_V_X' from the Opponent's row and name it 'avg_V_o_X'.
    # And 'days_since_last' -> 'days_since_last_o'
    # And 'avg_diff_P_X' -> 'avg_diff_P_o_X' (Wait, RData names: avg_diff_P_o_X?)
    # User List: avg_diff_P_o_X exists. 
    # Logic: avg_diff_P for Opponent = How much Opponent wins by on average.
    
    # Columns to copy from Opponent
    windows = [1, 4, 8, 12, 16, 32]
    cols_to_pull = ['avg_V_' + str(w) for w in windows] + \
                   ['avg_diff_P_' + str(w) for w in windows] + \
                   ['avg_P_' + str(w) for w in windows] + \
                   ['days_since_last']
                   
    # Select subset
    right = df[['Date', 'Team'] + cols_to_pull].copy()
    
    # Rename for merge
    rename_map = {'Team': 'Opponent'}
    for c in cols_to_pull:
        if c == 'days_since_last':
            rename_map[c] = 'days_since_last_o'
        elif c.startswith('avg_V_'):
            # avg_V_4 -> avg_V_o_4
            parts = c.split('_')
            rename_map[c] = f"avg_V_o_{parts[2]}"
        elif c.startswith('avg_diff_P_'):
            # avg_diff_P_4 -> avg_diff_P_o_4
            parts = c.split('_') # avg, diff, P, 4
            rename_map[c] = f"avg_diff_P_o_{parts[3]}"
        elif c.startswith('avg_P_'):
            # avg_P_4 -> avg_P_opp_4 (User Specified Name)
            parts = c.split('_') # avg, P, 4
            rename_map[c] = f"avg_P_opp_{parts[2]}"
            
    right = right.rename(columns=rename_map)
    
    # Merge
    merged = pd.merge(df, right, on=['Date', 'Opponent'], how='left')
    return merged

def build_features():
    print("🚀 Building Features (Exact RData Schema)...")
    
    
    # 1. Load History (Treasury now holds ALL history + 2025 season)
    print("📜 Loading RData Treasury (Single Source of Truth)...")
    df_full = get_rdata_treasury()
    
    if not df_full.empty:
        df_full['Date'] = pd.to_datetime(df_full['Date'])
        # Sort
        df_full = df_full.sort_values(['Team', 'Date'])
    else:
        print("❌ Error: No Treasury Data Found.")
        return pd.DataFrame()
        
    # Debug BKN Before Dedup
    bkn_pre = df_full[df_full['Team'].str.contains('Brooklyn')]
    print(f"DEBUG: BKN Rows Before Dedup: {len(bkn_pre)}")
    if not bkn_pre.empty:
        print(f"DEBUG: Last BKN Date Pre-Dedup: {bkn_pre['Date'].max()}")
        
    df_full = df_full.drop_duplicates(subset=['Date', 'Team'])
    
    # Debug BKN After Dedup
    bkn_post = df_full[df_full['Team'].str.contains('Brooklyn')]
    print(f"DEBUG: BKN Rows After Dedup: {len(bkn_post)}")
    if not bkn_post.empty:
        print(f"DEBUG: Last BKN Date Post-Dedup: {bkn_post['Date'].max()}")

    df_full = df_full.sort_values(['Team', 'Date'])
    df_calc = calculate_rolling(df_full)
    
    # 2.5 Calculate Matchup Metrics (Nemesis) -- NEW FIX
    df_calc = calculate_matchup_metrics(df_calc)
    
    # 3. Add Opponent Side (Self Join)
    df_final = add_opponent_metrics(df_calc)
    
    # 4. Add Context (Contextual)
    df_final['weekday'] = df_final['Date'].dt.day_name().str[:3].str.lower()
    df_final['month'] = df_final['Date'].dt.month_name().str[:3].str.lower()
    
    # 5. Nemesis (History Bridge) - REMOVED PLACEHOLDERS
    # History now flows through calculate_matchup_metrics
    
    # 6. Save
    df_final.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved Features: {OUTPUT_PATH} ({len(df_final)} rows)")
    print("   Schema aligned with RData Treasury.")

if __name__ == "__main__":
    build_features()
