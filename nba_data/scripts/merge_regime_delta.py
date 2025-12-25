
import pandas as pd
import json
import os

# Paths
REGIME_PATH = "processed/nba_regime_index_v1.json"
HISTORICAL_PATH = "data/nba_2008-2025.csv"
OUTPUT_PATH = "processed/regime_delta_dataset.csv"

# Team Mapping: Abbrev -> Full Name
# Based on common NBA abbreviations used in datasets
TEAM_MAP = {
    "atl": "Atlanta Hawks",
    "bos": "Boston Celtics",
    "bkn": "Brooklyn Nets",
    "nj": "New Jersey Nets", # Legacy
    "cha": "Charlotte Hornets",
    "chho": "Charlotte Hornets", # Variant
    "chi": "Chicago Bulls",
    "cle": "Cleveland Cavaliers",
    "dal": "Dallas Mavericks",
    "den": "Denver Nuggets",
    "det": "Detroit Pistons",
    "gs": "Golden State Warriors",
    "gsw": "Golden State Warriors",
    "hou": "Houston Rockets",
    "ind": "Indiana Pacers",
    "lac": "Los Angeles Clippers",
    "lal": "Los Angeles Lakers",
    "mem": "Memphis Grizzlies",
    "mia": "Miami Heat",
    "mil": "Milwaukee Bucks",
    "min": "Minnesota Timberwolves",
    "no": "New Orleans Pelicans",
    "nop": "New Orleans Pelicans",
    "noh": "New Orleans Hornets", # Legacy
    "ny": "New York Knicks",
    "nyk": "New York Knicks",
    "okc": "Oklahoma City Thunder",
    "orl": "Orlando Magic",
    "phi": "Philadelphia 76ers",
    "pho": "Phoenix Suns",
    "phx": "Phoenix Suns",
    "por": "Portland Trail Blazers",
    "sac": "Sacramento Kings",
    "sa": "San Antonio Spurs",
    "sas": "San Antonio Spurs",
    "tor": "Toronto Raptors",
    "uta": "Utah Jazz",
    "utah": "Utah Jazz",
    "was": "Washington Wizards",
    "wsh": "Washington Wizards"
}

def normalize_team(code):
    code = str(code).lower().strip()
    return TEAM_MAP.get(code, code) # Return code if not found (for debugging)

def run_merge():
    print("🔄 Loading Historical Data...")
    hist_df = pd.read_csv(HISTORICAL_PATH)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    
    # Normalize Home and Away teams
    # Note: data/nba_2008-2025.csv has 'home' and 'away' columns with abbrevs
    hist_df['home_full'] = hist_df['home'].apply(normalize_team)
    hist_df['away_full'] = hist_df['away'].apply(normalize_team)
    
    # We need to reshape HISTORICAL data to be "Team-Game" based to match Regime Index?
    # Regime Index is 1 row per TEAM per GAME. 
    # Historical Data is 1 row per GAME (Home vs Away).
    # We must "Explode" historical data to have 2 rows per game (Home perspective, Away perspective).
    
    print("💥 Exploding Historical Data (Game -> Team-Game)...")
    
    # Perspective: HOME
    home_df = hist_df.copy()
    home_df['team'] = home_df['home_full']
    home_df['opponent'] = home_df['away_full']
    home_df['is_home'] = True
    home_df['team_cover'] = home_df['id_spread'] # 1 if Home Covered? 
    # Wait, id_spread definition: "Spread outcome". Convention usually 1=Favorite Covered? or 1=Home Covered?
    # We need to check 'whos_favored'.
    # If whos_favored == 'home', spread is usually negative (e.g. -5).
    # If home_score + spread > away_score, Home Covers.
    # Let's assume id_spread logic for now, but best calculate manually if possible?
    # Let's just create 'spread_margin' = (TeamScore - OppScore) - Spread.
    # Actually, let's keep it simple: Just map the "id_spread" if valid, or recalculate.
    # To be safe, we rely on 'spread' (the line) and scores.
    
    
    
    # Standardize Score Names for the Perspective
    # home_df: team=home (score_home), opp=away (score_away)
    home_df['team_score'] = home_df['score_home']
    home_df['opp_score'] = home_df['score_away']
    
    # Perspective: AWAY
    away_df = hist_df.copy()
    away_df['team'] = away_df['away_full']
    away_df['opponent'] = away_df['home_full']
    away_df['is_home'] = False

    # away_df: team=away (score_away), opp=home (score_home)
    away_df['team_score'] = away_df['score_away']
    away_df['opp_score'] = away_df['score_home']
    away_df['opp_score'] = away_df['score_home']
    
    combined_hist = pd.concat([home_df, away_df], ignore_index=True)
    
    print("🔄 Loading Regime Index...")
    regime_df = pd.read_json(REGIME_PATH)
    regime_df['date'] = pd.to_datetime(regime_df['date'])
    
    print("🔗 Merging Datasets...")
    # Join on Date + Team
    # We select the normalized scores and spread identifiers
    merged = pd.merge(
        regime_df,
        combined_hist[['date', 'team', 'spread', 'total', 'id_spread', 'id_total', 'team_score', 'opp_score', 'whos_favored']],
        on=['date', 'team'],
        how='inner'
    )
    
    print(f"✅ Merge Complete. Rows: {len(merged)}")
    
    merged.to_csv(OUTPUT_PATH, index=False)
    print(f"💾 Saved Regime Delta Dataset to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_merge()
