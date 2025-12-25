
import os
import json
import glob
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from collections import defaultdict

# --- Configuration ---
GAMELOGS_DIR = "/Users/js/g9/nba_data/gamelogs_real"
OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine/candidates_2025.csv"
MIN_GAMES = 10
SEASON_START_DATE = datetime(2025, 10, 22) # Approx start of 2025-26 season
SEASON_END_DATE = datetime(2026, 6, 30)

def parse_iso_date(date_str):
    # Format: "2025-06-23T00:00:00.000+00:00"
    try:
        # Simplification: just take the first 10 chars YYYY-MM-DD
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except:
        return None

def extract_upsets():
    print("Scanning JSON gamelogs in gamelogs_real...")
    files = glob.glob(os.path.join(GAMELOGS_DIR, "*.json"))
    
    games_registry = {} # ID -> Game Info
    team_map = {} # ID -> Abbrev
    
    # 1. Build Game Registry
    print("Building Game Registry...")
    for filepath in tqdm(files):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check events
            events = data.get('events', {})
            for event_id, event in events.items():
                game_date_str = event.get('gameDate')
                game_date = parse_iso_date(game_date_str)
                
                if not game_date:
                    continue
                    
                # Filter for 2025-26 Season
                if not (SEASON_START_DATE <= game_date <= datetime.now()):
                    continue
                
                if event_id in games_registry:
                    continue
                    
                score_str = event.get('score') # "103-91"
                if not score_str:
                    continue
                    
                home_id = event.get('homeTeamId')
                away_id = event.get('awayTeamId')
                home_score = event.get('homeTeamScore')
                away_score = event.get('awayTeamScore')
                
                if not (home_id and away_id and home_score and away_score):
                    continue
                    
                # Mapping opponents
                opp = event.get('opponent', {})
                opp_id = opp.get('id')
                opp_abbr = opp.get('abbreviation')
                if opp_id and opp_abbr:
                    team_map[opp_id] = opp_abbr
                
                # We assume the 'player's team' is the one NOT in opponent
                # But we don't know the player's team ID easily from this perspective 
                # UNLESS we see the same ID as opponent in another file.
                # However, for the REGISTRY, we just need IDs and Scores.
                # We can fill Abbrevs later.
                
                games_registry[event_id] = {
                    "game_id": event_id, # ESPN ID
                    "date": game_date,
                    "home_id": home_id,
                    "away_id": away_id,
                    "home_score": int(home_score),
                    "away_score": int(away_score)
                }
                
        except Exception as e:
            continue
            
    print(f"Found {len(games_registry)} games in 2025-26 season range.")
    
    # Sort by date
    sorted_games = sorted(games_registry.values(), key=lambda x: x["date"])
    
    # 2. Calculate Records
    records = defaultdict(lambda: {"wins": 0, "losses": 0})
    upset_candidates = []
    
    for game in tqdm(sorted_games, desc="Calculating Upsets"):
        h_id = game["home_id"]
        a_id = game["away_id"]
        h_score = game["home_score"]
        a_score = game["away_score"]
        
        # Determine Winner
        if h_score > a_score:
            winner_id = h_id
            loser_id = a_id
        else:
            winner_id = a_id
            loser_id = h_id
            
        # Get Current Stats (Before Game)
        h_rec = records[h_id]
        a_rec = records[a_id]
        
        h_g = h_rec["wins"] + h_rec["losses"]
        a_g = a_rec["wins"] + a_rec["losses"]
        
        # Upset Logic
        if h_g >= MIN_GAMES and a_g >= MIN_GAMES:
            h_pct = h_rec["wins"] / h_g
            a_pct = a_rec["wins"] / a_g
            
            favorite_id = None
            underdog_id = None
            fav_pct = 0.0
            und_pct = 0.0
            
            if h_pct > 0.60 and a_pct < 0.40:
                favorite_id = h_id
                underdog_id = a_id
                fav_pct = h_pct
                und_pct = a_pct
            elif a_pct > 0.60 and h_pct < 0.40:
                favorite_id = a_id
                underdog_id = h_id
                fav_pct = a_pct
                und_pct = h_pct
            
            # Check Result
            if favorite_id and winner_id == underdog_id:
                # FOUND UPSET
                fav_name = team_map.get(favorite_id, f"ID_{favorite_id}")
                und_name = team_map.get(underdog_id, f"ID_{underdog_id}")
                
                upset_candidates.append({
                    "game_id": game["game_id"], # ESPN ID
                    "date": game["date"].strftime("%Y-%m-%d"),
                    "favorite": fav_name,
                    "underdog": und_name,
                    "fav_pct": round(fav_pct, 3),
                    "und_pct": round(und_pct, 3),
                    "winner": und_name,
                    "score_diff": abs(h_score - a_score)
                })
        
        # Update Records
        records[winner_id]["wins"] += 1
        records[loser_id]["losses"] += 1
        
    # Validating Team Names (Filling missing ones)
    warn_count = 0
    for u in upset_candidates:
        if "ID_" in u["favorite"] or "ID_" in u["underdog"]:
            warn_count += 1
            
    print(f"Identified {len(upset_candidates)} upsets.")
    if warn_count > 0:
        print(f"Warning: {warn_count} teams have missing names (ID only).")
        
    # Save
    df = pd.DataFrame(upset_candidates)
    if not df.empty:
        df.to_csv(OUTPUT_FILE, index=False)
        print(df.head())
        print(f"Saved to {OUTPUT_FILE}")
    else:
        print("No upsets found.")

if __name__ == "__main__":
    extract_upsets()
