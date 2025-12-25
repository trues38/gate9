
import pandas as pd
import json
import os
import glob
from datetime import datetime, timedelta

# Config
UPSET_LIBRARY_TAGGED = "/Users/js/g9/nba_data/quant_engine/upset_library_tagged.json"
GAMELOGS_DIR = "/Users/js/g9/nba_data/gamelogs"
OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine/upset_library_enriched.json"

def load_gamelogs(season_year):
    """
    Load all gamelogs for a specific season into a single DataFrame.
    """
    # Map season year to file pattern (e.g., 2013 -> gamelog_2013-14.csv)
    # The 'season' field in upset library is the start year (e.g. 2013 for 2013-14)
    next_year = str(season_year + 1)[-2:]
    season_str = f"{season_year}-{next_year}"
    
    # We need to find all player files for this season
    # But wait! We have team-level gamelogs? No, we have PLAYER gamelogs.
    # We need to aggregate player gamelogs to infer team schedule? 
    # Or checking if we have team gamelogs?
    # Based on previous tasks, we have player gamelogs. 
    # However, calculating Team Back-to-Backs from PLayer logs varies if players rest.
    # Strategy: Find ONE major player for the favorite team who played most games (e.g. top minutes).
    # Better Strategy: We only need DATE and TEAM.
    # Let's iterate through player logs until we find the Favorite Team's schedule for that season.
    
    # Correction: We should have 'gamelogs' structured by player? 
    # Let's assume we can load a few key players to reconstruct the team schedule.
    
    # Let's just walk the directory looking for a file that contains the team's schedule.
    # Actually, we can use the 'gamelogs_real' if available, but task says 'nba_data/gamelogs/*.csv'.
    # Let's look at one file to recall structure.
    return season_str

def get_team_schedule(team_abbr, season, game_date_str):
    """
    Reconstructs the team's schedule around the target date to determine Rest and Streak.
    Since we don't have a dedicated 'team_gamelog' table, we scan the csvs.
    This is expensive, so we will optimize by caching.
    """
    # For now, let's look for a file that matches the season pattern.
    # We will assume we can find *one* player on the team.
    pass

# We need a robust way to get Team Schedule from Player Logs.
# Helper: Extract all game dates and outcomes for a specific Team from a collection of CSVs.
# To make this efficient, I will scan the first CSV I find for `season_id` matching, 
# then filter by TEAM_ABBREVIATION == team_abbr.
# I might need to scan multiple files if the first player didn't play all games, but usually
# a starter plays enough to establish the dates.


def enrich_upsets():
    print(f"Checking input file: {UPSET_LIBRARY_TAGGED}")
    if not os.path.exists(UPSET_LIBRARY_TAGGED):
        print(f"Error: {UPSET_LIBRARY_TAGGED} not found.")
        return

    print("Loading JSON...")
    with open(UPSET_LIBRARY_TAGGED, 'r') as f:
        upsets = json.load(f)

    print(f"Enriching {len(upsets)} upsets with Hard Context...")

    # Cache for team schedules: Key="Season_Team", Value=DataFrame
    schedule_cache = {}

    enriched_count = 0

    for i, upset in enumerate(upsets):
        game_id = upset['game_id']
        date_str = upset['date']
        fav_team = upset['favorite']
        season = upset['season']
        
        # Format season string for glob
        next_year = str(season + 1)[-2:]
        season_file_suffix = f"{season}-{next_year}" # e.g. 2013-14
        
        cache_key = f"{season}_{fav_team}"
        
        team_games = None
        
        if cache_key in schedule_cache:
            team_games = schedule_cache[cache_key]
        else:
            # Find a CSV that contains this team's data for this season
            # We urge to look at ALL csvs in `nba_data/gamelogs` is too slow (thousands of players).
            # We need a hack. We know `scan_historical_upsets.py` already scanned them.
            # Maybe we can just find *any* CSV that has rows for this Team and Season?
            # Let's simple-scan the first 50 csvs.
            
            # Search pattern: gamelogs/*/gamelog_YYYY-YY.csv
            # We use recursive true with ** if supported, or just iterate subdirs
            # Simple approach: Check specific player dirs if known? No.
            # Let's try 2 levels deep
            season_pattern = f"gamelog_{season_file_suffix}.csv"
            found_schedule = False
            
            # Optimization: Just look at the first few directories to find a match
            # This is a bit 'hacky' but searching 4000 directories is slow in Python without index
            # Let's try to glob with limit
            
            print(f"   Searching for schedule in {season_file_suffix}...")
            # Use iglob for iterator
            candidates = glob.iglob(os.path.join(GAMELOGS_DIR, "*", season_pattern))
            
            for p_file in candidates:
                try:
                    # We only read the first few lines to check TEAM
                    # pd.read_csv with chunksize
                    chunk = pd.read_csv(p_file, nrows=5)
                    if 'TEAM_ABBREVIATION' in chunk.columns:
                        team_val = chunk['TEAM_ABBREVIATION'].iloc[0]
                        if team_val == fav_team:
                            # Found the team! Read full file
                             team_games = pd.read_csv(p_file).sort_values('GAME_DATE')
                             schedule_cache[cache_key] = team_games
                             found_schedule = True
                             # print(f"   Found schedule in {p_file}")
                             break
                except:
                    continue
                
                if found_schedule: break

            
            if not found_schedule:
                # print(f"Warning: Could not find schedule for {fav_team} in {season}")
                # Add default/null context
                upset['context'] = {
                    "rest_days": None,
                    "streak_type": None,
                    "streak_count": 0,
                    "location": None
                }
                continue

        # Now we have team_games df
        if team_games is not None:
             # Find current game index
            target_game = team_games[team_games['GAME_DATE'] == date_str]
            
            if target_game.empty:
                # Date mismatch (maybe timezone?) or player DNP
                # Try finding game by Game_ID?
                # Sometimes Game_ID in CSV is int, in JSON is string with padding.
                # CSV: 21300476 (int) or "0021300476"
                # JSON: "0021300476"
                
                # Try matching by ID suffix
                short_id = int(game_id)
                target_game = team_games[team_games['Game_ID'].astype(str).str.contains(str(short_id))]
            
            if not target_game.empty:
                idx = target_game.index[0]
                
                # 1. Location (Home/Away)
                matchup = target_game.at[idx, 'MATCHUP']
                # "OKC vs BKN" (Home) or "OKC @ BKN" (Away)
                location = "HOME" if "vs." in matchup or "vs" in matchup else "AWAY"
                
                # 2. Rest Days
                # Find previous game
                # Filter games BEFORE this date
                current_date = pd.to_datetime(date_str)
                team_games['dt'] = pd.to_datetime(team_games['GAME_DATE'])
                past_games = team_games[team_games['dt'] < current_date].sort_values('dt')
                
                rest_days = 3 # Default to "Rested"
                if not past_games.empty:
                    last_game_date = past_games.iloc[-1]['dt']
                    diff = (current_date - last_game_date).days
                    rest_days = diff - 1 # If consecutive days, diff is 1, rest is 0.
                    if rest_days < 0: rest_days = 0 
                
                # 3. Streak
                # Look at last 5 games WL
                streak_count = 0
                streak_type = "N/A"
                if not past_games.empty:
                    # Parse WL column
                    last_results = []
                    # We need to iterate backwards from the last game
                    # Limit to last 10 games to find streak
                    recent = past_games.tail(10)
                    # We need to ensure the rows are sorted strictly
                    # They are.
                    
                    # Logic: walk backwards
                    # But wait, did the csv have WL? Yes.
                    
                    w_or_l = recent['WL'].tolist()
                    if w_or_l:
                        current_streak_type = w_or_l[-1] # 'W' or 'L'
                        streak_type = current_streak_type
                        cnt = 0
                        for res in reversed(w_or_l):
                            if res == current_streak_type:
                                cnt += 1
                            else:
                                break
                        streak_count = cnt

                upset['context'] = {
                    "rest_days": int(rest_days),
                    "streak_type": streak_type,
                    "streak_count": int(streak_count),
                    "location": location
                }
                enriched_count += 1
            else:
                # Could not link game
                upset['context'] = {
                    "rest_days": None,
                    "streak_type": None,
                    "streak_count": 0,
                    "location": None
                }

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(upsets, f, indent=2)

    print(f"Enrichment Complete. Enriched {enriched_count}/{len(upsets)} games.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    enrich_upsets()
