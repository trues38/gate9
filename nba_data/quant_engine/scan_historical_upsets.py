
import os
import glob
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from collections import defaultdict

# --- Configuration ---
GAMELOGS_DIR = "/Users/js/g9/nba_data/gamelogs"
OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine/historical_upset_candidates.csv"
START_YEAR = 2011  # Season start year (e.g., 2011 for 2011-12)
END_YEAR = 2024    # Season start year (e.g., 2024 for 2024-25)
MIN_GAMES = 10

def parse_date(date_str):
    """Parses 'Mar 06, 2016' to datetime object."""
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except ValueError:
        return None

def scan_upsets():
    print(f"Scanning CSV gamelogs in {GAMELOGS_DIR}...")
    
    # 1. Gather all CSV files
    # Pattern: gamelogs/[PLAYER_ID]/gamelog_[SEASON].csv
    # We want seasons 2011-12 onwards.
    # filename example: 'gamelog_2015-16.csv'
    
    all_files = glob.glob(os.path.join(GAMELOGS_DIR, "*", "*.csv"))
    print(f"Found {len(all_files)} CSV files total.")
    
    # Registry: games[game_id] = {date, home, away, winner, loser, season}
    games_registry = {}
    
    for filepath in tqdm(all_files, desc="Indexing Games"):
        # Extract season from filename to skip early if possible
        filename = os.path.basename(filepath)
        # Check if season is within range
        # format: gamelog_YYYY-YY.csv
        try:
            season_start_str = filename.split('_')[1].split('-')[0]
            season_start = int(season_start_str)
            if not (START_YEAR <= season_start <= END_YEAR):
                continue
        except:
            continue
            
        try:
            df = pd.read_csv(filepath)
        except Exception:
            continue
            
        # Columns: Game_ID, GAME_DATE, MATCHUP, WL
        # Note: Game_ID is mixed case in some files
        
        # Normalize columns to uppercase for checking
        df.columns = [c.upper() for c in df.columns]
        
        required_cols = ['GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL']
        if not all(col in df.columns for col in required_cols):
            # print(f"Skipping {filename}: Missing columns. Found: {df.columns.tolist()}")
            continue
            
        for _, row in df.iterrows():
            game_id = row['GAME_ID']
            if game_id in games_registry:
                continue
                
            wl = row['WL']
            if pd.isna(wl) or wl not in ['W', 'L']:
                continue
                
            matchup = row['MATCHUP'] # "MEM vs. PHX" or "MEM @ DEN"
            date_str = row['GAME_DATE']
            game_date = parse_date(date_str)
            if not game_date:
                continue
                
            # Parse Matchup
            # "MEM vs. PHX" -> MEM is Home, PHX is Away
            # "MEM @ DEN" -> MEM is Away, DEN is Home
            
            try:
                if ' vs. ' in matchup:
                    parts = matchup.split(' vs. ')
                    team_a = parts[0]
                    team_b = parts[1]
                    home_team = team_a
                    away_team = team_b
                    # If WL=W, Team A won at Home.
                    # If WL=L, Team A lost at Home.
                    winner = team_a if wl == 'W' else team_b
                    loser = team_b if wl == 'W' else team_a
                elif ' @ ' in matchup:
                    parts = matchup.split(' @ ')
                    team_a = parts[0]
                    team_b = parts[1]
                    home_team = team_b
                    away_team = team_a
                    # If WL=W, Team A won Away.
                    # If WL=L, Team A lost Away.
                    winner = team_a if wl == 'W' else team_b
                    loser = team_b if wl == 'W' else team_a
                else:
                    continue
            except:
                continue
                
            games_registry[game_id] = {
                "game_id": game_id,
                "date": game_date,
                "season": season_start, # User "2015" for 2015-16
                "home_team": home_team,
                "away_team": away_team,
                "winner": winner,
                "loser": loser
            }

    print(f"Index complete. Found {len(games_registry)} unique games.")
    
    # 2. Analyze
    sorted_games = sorted(games_registry.values(), key=lambda x: x["date"])
    
    # Records: records[season][team] = {wins, losses}
    season_records = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0}))
    
    upset_candidates = []
    
    for game in tqdm(sorted_games, desc="Calculating Records"):
        season = game["season"]
        home = game["home_team"]
        away = game["away_team"]
        winner = game["winner"]
        loser = game["loser"]
        
        # Current Record Check (Before this game)
        home_stats = season_records[season][home]
        away_stats = season_records[season][away]
        
        h_g = home_stats["wins"] + home_stats["losses"]
        a_g = away_stats["wins"] + away_stats["losses"]
        
        if h_g >= MIN_GAMES and a_g >= MIN_GAMES:
            h_pct = home_stats["wins"] / h_g
            a_pct = away_stats["wins"] / a_g
            
            favorite = None
            underdog = None
            fav_pct = 0.0
            und_pct = 0.0
            
            # Simple Upset Logic
            # Favorite (>60%) vs Underdog (<40%)
            if h_pct > 0.60 and a_pct < 0.40:
                favorite = home
                underdog = away
                fav_pct = h_pct
                und_pct = a_pct
            elif a_pct > 0.60 and h_pct < 0.40:
                favorite = away
                underdog = home
                fav_pct = a_pct
                und_pct = h_pct
            
            # Look for Loss
            if favorite and winner == underdog:
                upset_candidates.append({
                    "game_id": game['game_id'],
                    "date": game['date'].strftime("%Y-%m-%d"),
                    "season": season,
                    "favorite": favorite,
                    "underdog": underdog,
                    "fav_pct": round(fav_pct, 3),
                    "und_pct": round(und_pct, 3),
                    "winner": winner
                })
        
        # Update Records
        season_records[season][winner]["wins"] += 1
        season_records[season][loser]["losses"] += 1
        
    df_upsets = pd.DataFrame(upset_candidates)
    if not df_upsets.empty:
        df_upsets.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Identified {len(df_upsets)} upsets.")
        print(df_upsets.head())
    else:
        print("No upsets found.")

if __name__ == "__main__":
    scan_upsets()
