
import pandas as pd
import json
import os
from datetime import timedelta

# Inputs
REGIME_PATH = "processed/nba_regime_index_v1.json"
RDATA_PATH = "processed/rdata_treasury_backup.csv"
OUTPUT_PATH = "processed/nba_validation_dataset.csv"

# Team Mapping (RData might have different names)
# If mismatch, we might need a map. Let's try exact first, then normalize.
# Common RData/ESPN differences: "LA Clippers" vs "Los Angeles Clippers"
TEAM_MAP_RDATA_TO_REGIME = {
    "Rockets": "Houston Rockets",
    "Magic": "Orlando Magic",
    "Nets": "Brooklyn Nets",
    "Pacers": "Indiana Pacers",
    "Pelicans": "New Orleans Pelicans",
    "Grizzlies": "Memphis Grizzlies",
    "Heat": "Miami Heat",
    "Bucks": "Milwaukee Bucks",
    "Timberwolves": "Minnesota Timberwolves",
    "Hornets": "Charlotte Hornets",
    "Knicks": "New York Knicks",
    "Thunder": "Oklahoma City Thunder",
    "76ers": "Philadelphia 76ers",
    "Suns": "Phoenix Suns",
    "Blazers": "Portland Trail Blazers",
    "Kings": "Sacramento Kings",
    "Spurs": "San Antonio Spurs",
    "Raptors": "Toronto Raptors",
    "Jazz": "Utah Jazz",
    "Wizards": "Washington Wizards",
    "Hawks": "Atlanta Hawks",
    "Celtics": "Boston Celtics",
    "Mavericks": "Dallas Mavericks",
    "Nuggets": "Denver Nuggets",
    "Pistons": "Detroit Pistons",
    "Warriors": "Golden State Warriors",
    "Cavaliers": "Cleveland Cavaliers",
    "Lakers": "Los Angeles Lakers",
    "Clippers": "Los Angeles Clippers",
    "Bulls": "Chicago Bulls",
}

# Reverse just in case RData uses full names
# Let's inspect RData team names first? 
# We'll assume RData might use short names or full names.
# Best approach: Normalize both to simple version.

def normalize_team(name):
    name = str(name).strip()
    if name in TEAM_MAP_RDATA_TO_REGIME:
        return TEAM_MAP_RDATA_TO_REGIME[name]
    # Check if any value in map matches
    for k, v in TEAM_MAP_RDATA_TO_REGIME.items():
        if name == v: 
            return v
        if name in v: # "Lakers" in "Los Angeles Lakers"
            return v
    return name

def run_merge():
    print("🔄 Loading Regime Index...")
    regime_df = pd.read_json(REGIME_PATH)
    regime_df['date'] = pd.to_datetime(regime_df['date'])
    
    print("🔄 Loading RData Treasury...")
    rdata_df = pd.read_csv(RDATA_PATH)
    rdata_df['Date'] = pd.to_datetime(rdata_df['Date']) # Ensure Date format
    
    # Normalize Teams in RData
    print("🛠 Normalizing RData Team Names...")
    rdata_df['Normalized_Team'] = rdata_df['Team'].apply(normalize_team)
    
    # Select columns to merge from RData
    # We need: Odds, Opponent Odds, maybe Points?
    rdata_subset = rdata_df[[
        'Date', 'Normalized_Team', 'odds', 'odds.opponent', 'Points', 'OpponentPoints', 'Team_Zone', 'Opponent_Zone'
    ]].copy()
    
    rdata_subset.rename(columns={
        'Date': 'date',
        'Normalized_Team': 'team',
        'odds': 'r_odds_team',
        'odds.opponent': 'r_odds_opp'
    }, inplace=True)
    
    # Merge
    print("🔗 Merging Datasets...")
    merged_df = pd.merge(
        regime_df,
        rdata_subset,
        on=['date', 'team'],
        how='inner' # We only want validated rows (Intersection)
    )
    
    print(f"✅ Merge Complete. Rows: {len(merged_df)} (Original Regime: {len(regime_df)})")
    
    if len(merged_df) < len(regime_df) * 0.5:
        print("⚠️ Warning: Low Merge Rate. Check Team Names or Date Formats.")
        # Debug
        print("Sample Regime Teams:", regime_df['team'].unique()[:5])
        print("Sample RData Teams (Normalized):", rdata_df['Normalized_Team'].unique()[:5])
    
    merged_df.to_csv(OUTPUT_PATH, index=False)
    print(f"💾 Saved Validation Dataset to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_merge()
