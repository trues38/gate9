import json
import os
import argparse
import time
import requests
import re
import logging
import csv
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
DATA_DIR = "nba_data"
LOGS_DIR = os.path.join(DATA_DIR, "gamelogs")
STORIES_DIR = os.path.join(DATA_DIR, "stories_raw")

# Ensure stories directory exists
os.makedirs(STORIES_DIR, exist_ok=True)

# Team Mapping: NBA API Tri-codes -> ESPN API Abbreviations
# Most match, but some might differ (e.g. PHX, UTA, NOK->NOP?)
# We will do a fuzzy match or standard check.
# The standard NBA tri-codes are usually consistent.
# Exception: NOH (New Orleans Hornets) vs NOP (Pelicans). 
# BKN (Brooklyn) vs NJN (New Jersey).
# SEA (Seattle) vs OKC.

def load_game_logs(season):
    """
    Load all game log CSVs for a specific season and extract unique game IDs.
    Returns a list of dicts: {'game_id': '...', 'date': '...', 'matchup': '...'}
    """
    unique_games = {}
    
    print(f"Scanning game logs for season {season}...")
    
    file_count = 0
    for root, dirs, files in os.walk(LOGS_DIR):
        for file in files:
            if f"gamelog_{season}" in file and file.endswith(".csv"):
                file_count += 1
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            game_id = row.get("Game_ID")
                            date_str = row.get("GAME_DATE")
                            matchup = row.get("MATCHUP")
                            
                            if not (game_id and date_str and matchup):
                                continue
                            
                            if game_id not in unique_games:
                                unique_games[game_id] = {
                                    'game_id': game_id,
                                    'date': date_str,
                                    'matchup': matchup
                                }
                except Exception as e:
                    pass
                    
    print(f"Found {file_count} log files.")
    print(f"Identified {len(unique_games)} unique games for {season}.")
    return list(unique_games.values())

def parse_date_to_espn_format(date_str):
    """
    Converts "Apr 15, 2015" (NBA Log format) into "20150415" (ESPN API format).
    """
    try:
        # Expected format: "Apr 15, 2015" OR "DEC 25, 2014"
        # strip quotes just in case
        clean = date_str.replace('"', '').strip()
        dt = datetime.strptime(clean, "%b %d, %Y")
        return dt.strftime("%Y%m%d")
    except Exception as e:
        logging.error(f"Date parse error for {date_str}: {e}")
        return None

def fetch_espn_game_id(date_str, distinct_teams):
    """
    Uses ESPN Scoreboard API to find the game ID for a given date and teams.
    distinct_teams: list of team abbrs, e.g. ['CHI', 'ATL']
    API: http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20150415
    """
    yyyymmdd = parse_date_to_espn_format(date_str)
    if not yyyymmdd:
        return None
        
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yyyymmdd}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        events = data.get('events', [])
        
        # Look for matching event
        for event in events:
            # Check competitors
            comps = event.get('competitions', [{}])[0].get('competitors', [])
            if len(comps) < 2: continue
            
            team1 = comps[0]['team']['abbreviation']
            team2 = comps[1]['team']['abbreviation']
            
            # Check if OUR teams match specific game
            # Note: NBA API might use NOH, ESPN uses NOP. PHX vs PHX.
            # We check if BOTH distinct_teams are in [team1, team2]
            # Handling some historical mapping could be needed, but usually TRIcodes match.
            
            match_count = 0
            for t in distinct_teams:
                # Basic normalization
                t_norm = t.upper()
                if t_norm == 'NOH': t_norm = 'NOP' # Example fix
                if t_norm == 'NJN': t_norm = 'BKN'
                
                if t_norm in [team1, team2]:
                    match_count += 1
            
            # Strict match: need both teams
            if match_count == 2:
                return event['id']
                
            # Lenient match for edge cases? 
            # If we only match 1 team, it's ambiguous if that team played double header? (Impossible in NBA)
            # Maybe safe to return if 1 matches? NO, could match wrong game if we are lazy.
            # Let's stick to 2.
            
        return None

    except Exception as e:
        logging.error(f"Scoreboard fetch failed for {date_str}: {e}")
        return None

def fetch_espn_recap(espn_game_id):
    """
    Fetches JSON summary.
    """
    api_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={espn_game_id}"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        data = resp.json()
        article = data.get('article', {})
        story_html = article.get('story', '')
        
        if not story_html:
            return None, None

        headline = article.get('headline', '')
        
        # Clean HTML (minimal tags usually in this JSON, mostly <p>)
        # Actually ESPN API returns raw HTML paragraphs.
        # We can use simple regex or just save raw and process later.
        # Impl plan said "text".
        # Let's clean it properly to just text.
        text = re.sub(r'<[^>]+>', '', story_html) 
        text = text.replace("&nbsp;", " ")
        text = text.strip()
        
        return text, headline
        
    except Exception as e:
        logging.error(f"Summary fetch failed for {espn_game_id}: {e}")
        return None, None

def crawl_individual_game(game_info):
    game_id = game_info['game_id']
    date_str = game_info['date']
    matchup = game_info['matchup'] # "CHI @ ATL"
    
    save_path = os.path.join(STORIES_DIR, f"story_{game_id}.json")
    if os.path.exists(save_path):
        return "Exists"

    # Extract teams from matchup
    # "CHI @ ATL" or "CHI vs. ATL"
    # Regex to grab all CAPS words
    teams = re.findall(r'([A-Z]{3})', matchup)
    if len(teams) < 2:
        logging.warning(f"Skipping {game_id}: Could not parse teams from {matchup}")
        return "Skipped"
    
    teams = list(set(teams)) # strict? no, just [TeamA, TeamB]
    
    # 1. Discover ESPN ID
    espn_id = fetch_espn_game_id(date_str, teams)
    
    if not espn_id:
        logging.warning(f"[MISSING ID] Could not find ESPN game for {matchup} on {date_str}")
        return "Missing"
        
    # 2. Fetch Story
    body, headline = fetch_espn_recap(espn_id)
    
    if not body:
        logging.warning(f"[NO STORY] Found ID {espn_id} but no story for {matchup}")
        return "NoStory"
        
    # 3. Save
    story_data = {
        "game_id": game_id,
        "espn_id": espn_id,
        "date": date_str,
        "matchup": matchup,
        "headline": headline,
        "body": body,
        "source": "espn_api",
        "crawled_at": time.time()
    }
    
    with open(save_path, 'w') as f:
        json.dump(story_data, f, indent=2, ensure_ascii=False)
        
    logging.info(f"[SAVED] {game_id} | {headline}")
    return "Saved"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=str, default="2023-24")
    args = parser.parse_args()
    
    season = args.season
    games = load_game_logs(season)
    
    if not games:
        print("No games found.")
        return

    print(f"Starting API Crawl for {len(games)} games...")
    stats = {"Saved": 0, "Exists": 0, "Missing": 0, "NoStory": 0, "Skipped": 0}
    
    for i, game in enumerate(games):
        status = crawl_individual_game(game)
        stats.get(status, 0) # increment safely?
        if status in stats: stats[status] += 1
        
        # Be nice to API
        time.sleep(0.5)
        
        if (i+1) % 10 == 0:
            print(f"Progress: {i+1}/{len(games)} | Stats: {stats}")
            
    print(f"Done. Final Stats: {stats}")

if __name__ == "__main__":
    main()
