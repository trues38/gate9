import pandas as pd
import duckdb
import json
import numpy as np
from lab_leakage_guard import scan_features

# CONFIG
DB_PATH = "nba_sql.duckdb"
ODDS_PATH = "g9_core_export/DATA/nba_2008-2025.csv"
REGIME_PATH = "g9_core_export/DATA/nba_regime_index.json"

# SPLIT DATES
TRAIN_END = "2022-06-30" # Train: Start to 21-22 Season
VALID_START = "2022-10-01"
VALID_END = "2023-06-30" # Valid: 22-23 Season
TEST_START = "2023-10-01" # Test: 23-24 Season (OOS)

def load_regime_labels():
    print("Loading Labels...")
    with open(REGIME_PATH, 'r') as f:
        data = json.load(f)
    rows = []
    for info in data:
        rows.append({
            'game_id': info.get('id'),
            'Date': info.get('date'),
            'Team': info.get('team'), # Team perspective
            'Regime_Label': info.get('regime_type')
        })
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Team'] = df['Team'].str.upper().str.strip()
    return df

def load_features():
    print("Loading RData Features...")
    con = duckdb.connect(DB_PATH)
    # Pre-game Metrics Only
    query = """
        SELECT 
            Date, Team, 
            NetRtg_Sea, NetRtg_L10,
            avg_P_4 as Pace_L4, avg_P_16 as Pace_L16,
            avg_V_8 as Vol_Opp,
            days_since_last as Rest,
            games_played as GP
        FROM rdata_treasury
    """
    df = con.execute(query).fetchdf()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Team'] = df['Team'].str.upper().str.strip()
    return df

def load_odds():
    print("Loading Odds...")
    df = pd.read_csv(ODDS_PATH)
    df['date'] = pd.to_datetime(df['date'])
    return df

def build_dataset():
    labels = load_regime_labels()
    features = load_features()
    odds = load_odds()
    
    # Merge Features
    print("Merging Metrics...")
    df = pd.merge(labels, features, on=['Date', 'Team'], how='inner')
    
    # Merge Odds (Need Mapping)
    print("Merging Odds...")
    # Add 'odds_spread', 'odds_total', 'implied_prob'
    # Mapping Logic (Simplified for Lab)
    mapping = {
        'ATLANTA HAWKS': 'atl', 'BOSTON CELTICS': 'bos', 'BROOKLYN NETS': 'bkn', 'CHARLOTTE HORNETS': 'cha',
        'CHICAGO BULLS': 'chi', 'CLEVELAND CAVALIERS': 'cle', 'DALLAS MAVERICKS': 'dal', 'DENVER NUGGETS': 'den',
        'DETROIT PISTONS': 'det', 'GOLDEN STATE WARRIORS': 'gsw', 'HOUSTON ROCKETS': 'hou', 'INDIANA PACERS': 'ind',
        'LA CLIPPERS': 'lac', 'LOS ANGELES LAKERS': 'lal', 'MEMPHIS GRIZZLIES': 'mem', 'MIAMI HEAT': 'mia',
        'MILWAUKEE BUCKS': 'mil', 'MINNESOTA TIMBERWOLVES': 'min', 'NEW ORLEANS PELICANS': 'nop', 'NEW YORK KNICKS': 'nyk',
        'OKLAHOMA CITY THUNDER': 'okc', 'ORLANDO MAGIC': 'orl', 'PHILADELPHIA 76ERS': 'phi', 'PHOENIX SUNS': 'phx',
        'PORTLAND TRAIL BLAZERS': 'por', 'SACRAMENTO KINGS': 'sac', 'SAN ANTONIO SPURS': 'sas', 'TORONTO RAPTORS': 'tor',
        'UTAH JAZZ': 'uta', 'WASHINGTON WIZARDS': 'was'
    }
    
    # Vectorized mapping risky if messy strings. Loop safer for lab.
    odds_col_spread = []
    odds_col_total = []
    odds_col_moneyline = []
    
    # Optimized: Create Lookup Dict from Odds
    odds_lookup = {} # (Date, TeamCode) -> Row
    for idx, row in odds.iterrows():
        odds_lookup[(row['date'], row['home'])] = row
        odds_lookup[(row['date'], row['away'])] = row
        
    odds_col_favored = [] # New
        
    for idx, row in df.iterrows():
        team_code = mapping.get(row['Team'])
        match = odds_lookup.get((row['Date'], team_code))
        
        # Fuzzy Date Fallback
        if match is None:
             match = odds_lookup.get((row['Date'] + pd.Timedelta(days=1), team_code))
        
        if match is not None:
            odds_col_spread.append(match['spread'])
            odds_col_total.append(match['total'])
            odds_col_favored.append(match['whos_favored']) # 'home' or 'away'
            # Moneyline
            if team_code == match['home']:
                odds_col_moneyline.append(match['moneyline_home'])
            else:
                odds_col_moneyline.append(match['moneyline_away'])
        else:
            odds_col_spread.append(None)
            odds_col_total.append(None)
            odds_col_favored.append(None)
            odds_col_moneyline.append(None)
            
    df['Odds_Spread'] = odds_col_spread
    df['Odds_Total'] = odds_col_total
    df['Odds_Favored'] = odds_col_favored
    df['Moneyline'] = odds_col_moneyline
    
    # Drop Missing Odds
    df = df.dropna(subset=['Odds_Spread'])
    
    # LEAKAGE GUARD
    print("Running Leakage Guard...")
    cols_to_use = [
        'NetRtg_Sea', 'NetRtg_L10', 'Pace_L4', 'Pace_L16', 'Vol_Opp', 'Rest', 'GP',
        'Odds_Spread', 'Odds_Total', 'Moneyline', 'Odds_Favored', 'Regime_Label'
    ]
    scan_features(cols_to_use) # Raises Error if Banned Features found
    
    # Add Meta Columns for CSV export (Post-Scan)
    cols_export = ['Date', 'Team'] + cols_to_use
    
    # SAVE SPLITS
    print("Splitting...")
    train = df[df['Date'] <= TRAIN_END][cols_export]
    valid = df[(df['Date'] >= VALID_START) & (df['Date'] <= VALID_END)][cols_export]
    test = df[df['Date'] >= TEST_START][cols_export] # 24-25 Season
    
    print(f"Train: {len(train)}, Valid: {len(valid)}, Test: {len(test)}")
    
    train.to_csv("processed/lab_train.csv", index=False)
    valid.to_csv("processed/lab_valid.csv", index=False)
    test.to_csv("processed/lab_test.csv", index=False)
    
    # JSONL Export for LLM (Test Set)
    # Include Metadata for Prompt
    # Need to keep Date and Team for JSONL reference, even if not in ML cols
    test_meta = df[df['Date'] >= TEST_START].copy()
    
    jsonl_path = "processed/lab_test.jsonl"
    with open(jsonl_path, 'w') as f:
        for idx, row in test_meta.iterrows():
            record = {
                "id": f"{row['Date'].strftime('%Y%m%d')}_{row['Team']}",
                "date": row['Date'].strftime('%Y-%m-%d'),
                "team": row['Team'],
                "features": {
                    "net_rtg_sea": round(row['NetRtg_Sea'], 1),
                    "net_rtg_L10": round(row['NetRtg_L10'], 1),
                    "pace_L4": round(row['Pace_L4'], 1),
                    "rest": int(row['Rest']),
                    "spread": row['Odds_Spread'],
                    "total": row['Odds_Total'],
                    "favored_team": row['Odds_Favored']
                },
                "label": row['Regime_Label']
            }
            f.write(json.dumps(record) + "\n")
            
    print("Lab Datasets Created Successfully.")

if __name__ == "__main__":
    build_dataset()
