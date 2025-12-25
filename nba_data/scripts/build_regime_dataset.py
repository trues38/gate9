import pandas as pd
import duckdb
import json
import numpy as np

# CONFIG
DB_PATH = "nba_sql.duckdb"
REGIME_PATH = "g9_core_export/DATA/nba_regime_index.json"
TRAIN_START = "2015-10-01"
TRAIN_END = "2023-06-30"
TEST_START = "2023-10-01"
TEST_END = "2024-06-30"

def load_labels():
    print("Loading Regime Labels...")
    with open(REGIME_PATH, 'r') as f:
        data = json.load(f)
    
    # Flatten JSON to List
    rows = []
    for info in data:
        # info keys: 'date', 'team', 'regime_type', ...
        rows.append({
            'game_id': info.get('id'),
            'Date': info.get('date'),
            'Home': info.get('team'), # Team in regime index is the team the regime applies to
            'Regime_Label': info.get('regime_type'),
            'Margin': info.get('score_margin', 0)
        })
    return pd.DataFrame(rows)

def load_features():
    print("Loading Features from DuckDB...")
    con = duckdb.connect(DB_PATH)
    # Fetch Core Quant Features
    query = """
        SELECT 
            Date, Team, 
            NetRtg_Sea, NetRtg_L10,
            avg_P_4 as Pace_L4, avg_P_16 as Pace_L16,
            avg_V_8 as Vol_Opp,
            days_since_last as Rest
        FROM rdata_treasury 
        WHERE Date >= '2015-01-01'
    """
    df = con.execute(query).fetchdf()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Team'] = df['Team'].str.upper().str.strip()
    return df

def compute_tags(row):
    # Pre-game Cause Tags Logic (Heuristic/Proxy)
    tags = {}
    
    # 1. INJURY_SHOCK (Proxy: High Volatility?)
    # Without injury data, we use Volatility as proxy for "Stability Shock"
    tags['INJURY_SHOCK'] = 1 if row.get('Vol_Opp', 0) > 1.2 else 0
    
    # 2. RETURN_BOOST (Proxy: Rest > 3 + Trend Up?)
    tags['RETURN_BOOST'] = 0 # Cannot calc without roster
    
    # 3. SCHEDULE_CRUNCH (Rest=0 or Rest=1 after road trip - cant detect road trip easily)
    tags['SCHEDULE_CRUNCH'] = 1 if row.get('Rest', 0) == 0 else 0
    
    # 4. REST_EDGE (RestDiff > 2? Need opponent)
    # Will do in merge phase if possible, else skip for row-based
    
    # 5. PACE_SQUEEZE
    tags['PACE_SQUEEZE'] = 1 if row.get('Pace_L4', 99) < 96 else 0
    
    # 6. DEFENSE_LOCK
    # Proxy: DefRtg < 110 (using Season DefRtg proxy from NetRtg - OffRtg? No OffRtg.)
    # Use DefRtg_Sea if available (fetched above)
    tags['DEFENSE_LOCK'] = 1 if row.get('DefRtg_Sea', 115) < 110 else 0
    
    # 7. STAR_USAGE_SPIKE (Proxy: Volatility Low? No, High Usage = High Volatility usually)
    tags['STAR_USAGE_SPIKE'] = 1 if row.get('Vol_Opp', 0) > 1.5 else 0
    
    # 8. MOTIVATION_EDGE (Skip)
    
    return pd.Series(tags)

def build_dataset():
    df_labels = load_labels()
    df_labels['Date'] = pd.to_datetime(df_labels['Date'])
    df_labels['Home'] = df_labels['Home'].str.upper().str.strip()
    
    df_features = load_features()
    
    print("Merging Data...")
    # Merge on Date + Home Team
    # Feature Data is per Team. We need to attach Home Team Features to the Game Label.
    # (Simplified: Only using Home Team Features for prediction for v1)
    
    df_full = pd.merge(
        df_labels, 
        df_features, 
        left_on=['Date', 'Home'], 
        right_on=['Date', 'Team'], 
        how='inner'
    )
    
    print("Computing Tags...")
    tag_cols = df_full.apply(compute_tags, axis=1)
    df_full = pd.concat([df_full, tag_cols], axis=1)
    
    # Calculate EDGE SCORE Proxy
    # Edge = 50 + (NetRtg_Sea * 2) + (NetRtg_L10 - NetRtg_Sea)*1.5
    df_full['Edge_Score'] = 50 + (df_full['NetRtg_Sea'] * 2) + ((df_full['NetRtg_L10'] - df_full['NetRtg_Sea']) * 1.5)
    df_full['Edge_Score'] = df_full['Edge_Score'].clip(0, 100)
    
    # Split
    print("Splitting Datasets...")
    train = df_full[(df_full['Date'] >= TRAIN_START) & (df_full['Date'] <= TRAIN_END)]
    test = df_full[(df_full['Date'] >= TEST_START) & (df_full['Date'] <= TEST_END)]
    
    print(f"Train Size: {len(train)}")
    print(f"Test Size: {len(test)}")
    
    train.to_csv("processed/regime_train.csv", index=False)
    test.to_csv("processed/regime_test.csv", index=False)
    print("Datasets Saved.")

if __name__ == "__main__":
    build_dataset()
