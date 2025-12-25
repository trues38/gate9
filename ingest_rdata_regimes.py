
import pyreadr
import pandas as pd
import json
import os

# Configuration
INPUT_FILE = "/Users/js/Downloads/NBA_games_info.RData"
OUTPUT_FILE = "/Users/js/g9/nba_data/regimes/historical_odds_regimes.json"

def classify_tier(odds):
    # Tier 4: < 1.15 (-13.0+)
    if odds <= 1.10: return "Tier 4 (Miracle)"
    
    # Tier 3: 1.15 ~ 1.25 (-9.5 ~ -12.0)
    if odds <= 1.25: return "Tier 3 (Danger)"
    
    # Tier 2: 1.25 ~ 1.36 (-6.5 ~ -9.0)
    # Note: User said 1.35, I'll extend slightly to 1.36 to catch boundary
    if odds <= 1.36: return "Tier 2 (Caution)"
    
    # Tier 1: 1.36 ~ 1.55 (-4.5 ~ -6.0)
    if odds <= 1.60: return "Tier 1 (Trap)"
    
    return "Tier 0 (Neutral/Weak Fav)"

def run_ingestion():
    print(f"Loading {INPUT_FILE}...")
    try:
        data = pyreadr.read_r(INPUT_FILE)
        df = data['df'] # The object name 'df' we saw in inspection
    except Exception as e:
        print(f"Error loading RData: {e}")
        return

    print(f"Total rows: {len(df)}")
    
    # Filter for Home Games only to avoid duplicates (assuming 'local' == 1 means Home perspective)
    # The dataset seems to have both? Or need to check. 
    # Inspection showed local=1 for first 3 rows.
    # We will assume 'local' column exists and filter local==1
    if 'local' in df.columns:
        df = df[df['local'] == 1.0].copy()
        print(f"Home games only: {len(df)}")
        
    games = []
    
    # Iterate
    for idx, row in df.iterrows():
        try:
            # Extract basic info
            date = str(row['Date'])
            home = row['Team']
            away = row['Opponent']
            h_score = int(row['Points'])
            a_score = int(row['OpponentPoints'])
            h_odds = float(row['odds'])
            
            # Skip invalid odds
            if pd.isna(h_odds) or h_odds <= 1.0:
                continue
                
            # We are interested in FAVORITES (Home or Away)
            # But the row is Home Perspective.
            # If h_odds < 1.60 -> Home is Favorite
            # If h_odds > 2.50 (impliled Away Fav roughly? No, we need Away Odds)
            # Row has 'odds.opponent'.
            a_odds = float(row['odds.opponent']) if 'odds.opponent' in row else 99.0
            
            fav_team = None
            fav_odds = 0.0
            is_home_fav = False
            
            if h_odds <= 1.60:
                fav_team = home
                fav_odds = h_odds
                is_home_fav = True
            elif a_odds <= 1.60:
                fav_team = away
                fav_odds = a_odds
                is_home_fav = False
            
            if not fav_team:
                continue # Not a strong favorite game
                
            # Determine Outcome
            # Did the Favorite WIN?
            fav_won = False
            margin = 0
            if is_home_fav:
                margin = h_score - a_score
                fav_won = (margin > 0)
            else:
                margin = a_score - h_score
                fav_won = (margin > 0)
                
            # Classify Tier
            tier = classify_tier(fav_odds)
            
            # Record
            game_record = {
                "date": date,
                "tier": tier,
                "fav_team": str(fav_team),
                "und_team": str(away if is_home_fav else home),
                "fav_odds": round(fav_odds, 2),
                "margin": margin,
                "is_upset": not fav_won,
                "score_str": f"{h_score}-{a_score} ({'H' if is_home_fav else 'A'} Fav)"
            }
            games.append(game_record)
            
        except Exception as ex:
            continue
            
    print(f"Processed {len(games)} valid Favorite games.")
    
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(games, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_ingestion()
