
import requests
import json
import os
import time
from datetime import date, timedelta, datetime

# Configuration
START_DATE = date(2025, 10, 21) # Regular Season Start
END_DATE = date(2025, 12, 19)   # Today
OUTPUT_DIR = "nba_betting_report/input"
OS_MKDIR = True

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"    ⚠️ Request failed: {e}, retrying ({i+1}/{retries})...")
            time.sleep(1)
    return None

def parse_stat_group(stat_group):
    """
    Map ESPN stat group list to a dictionary for easier access.
    Returns: dict { 'name': 'value' }
    """
    stats = {}
    if not stat_group:
        return stats
        
    for item in stat_group:
        name = item.get('name')
        val = item.get('displayValue') # usually string like "41-89" or "14"
        stats[name] = val
    return stats

def parse_split_stat(value_str):
    """Parses 'Made-Attempted' string (e.g., '41-89') into (41, 89)."""
    if not value_str or '-' not in value_str:
        return 0, 0
    try:
        m, a = value_str.split('-')
        return int(m), int(a)
    except:
        return 0, 0

def get_stats_block(team_data, points, opp_points):
    """
    Extracts required stats from ESPN team data block.
    """
    # Flatten the statistics list
    stats_map = {}
    for group in team_data.get('statistics', []):
        name = group.get('name')
        # Check displayValue first, sometimes value is different
        val = group.get('displayValue')
        stats_map[name] = val

    # Parse Fields
    fg_m, fg_a = parse_split_stat(stats_map.get('fieldGoalsMade-fieldGoalsAttempted'))
    fg3_m, fg3_a = parse_split_stat(stats_map.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'))
    ft_m, ft_a = parse_split_stat(stats_map.get('freeThrowsMade-freeThrowsAttempted'))
    
    return {
        "points": int(points),
        "fieldGoalsMade": fg_m,
        "fieldGoalsAttempted": fg_a,
        "threePointFieldGoalsMade": fg3_m,
        "threePointFieldGoalsAttempted": fg3_a,
        "freeThrowsMade": ft_m,
        "freeThrowsAttempted": ft_a,
        "offensiveRebounds": int(stats_map.get('offensiveRebounds', 0)),
        "defensiveRebounds": int(stats_map.get('defensiveRebounds', 0)),
        "totalRebounds": int(stats_map.get('totalRebounds', 0)),
        "totalTurnovers": int(stats_map.get('totalTurnovers', 0)),
        "plusMinus": int(points) - int(opp_points)
    }

def process_date(target_date):
    date_str_api = target_date.strftime("%Y%m%d")
    date_str_file = target_date.strftime("%Y-%m-%d")
    
    print(f"📅 Processing {date_str_file}...")
    
    # 1. Fetch Scoreboard
    sb_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str_api}"
    sb_data = fetch_json(sb_url)
    
    if not sb_data:
        print("  ❌ Failed to fetch scoreboard.")
        return

    daily_games = []
    events = sb_data.get('events', [])
    print(f"  Found {len(events)} events.")
    
    for evt in events:
        # Only process finished games (or check if wanted live? request implied past)
        status = evt.get('status', {}).get('type', {}).get('completed', False)
        # We can include finished games. 
        if not status:
            # Skip if not completed (optional, strict interpretation of 'proceeded games')
            continue
            
        game_id = evt.get('id')
        
        # Identify Home/Away from Competitions
        full_competitions = evt.get('competitions', [])[0]
        competitors = full_competitions.get('competitors', [])
        
        home_comp = next((c for c in competitors if c.get('homeAway') == 'home'), None)
        away_comp = next((c for c in competitors if c.get('homeAway') == 'away'), None)
        
        if not home_comp or not away_comp:
            continue
            
        home_abbr = home_comp.get('team', {}).get('abbreviation')
        away_abbr = away_comp.get('team', {}).get('abbreviation')
        
        # Odds extraction
        odds_list = full_competitions.get('odds', [])
        market_line = 0.0
        if odds_list:
            try:
                # check 'details'
                details = odds_list[0].get('details', '')
                if details:
                    parts = details.split()
                    if len(parts) >= 2:
                        val = float(parts[-1])
                        spread_team = parts[0]
                        if spread_team == home_abbr:
                            market_line = val
                        elif spread_team == away_abbr:
                            market_line = -val 
            except:
                market_line = 0.0
        
        # 2. Fetch Detailed Boxscore
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        summary_data = fetch_json(summary_url)
        
        if not summary_data or 'boxscore' not in summary_data or 'teams' not in summary_data['boxscore']:
            print(f"  ⚠️ Missing boxscore for {game_id}")
            continue
            
        bs_teams = summary_data['boxscore']['teams']
        
        # Identify Home/Away in Boxscore
        home_bs = next((t for t in bs_teams if t.get('team', {}).get('abbreviation') == home_abbr), None)
        away_bs = next((t for t in bs_teams if t.get('team', {}).get('abbreviation') == away_abbr), None)
        
        if not home_bs or not away_bs:
            continue
            
        home_score = int(home_comp.get('score', 0))
        away_score = int(away_comp.get('score', 0))
        
        # Extract Stats
        try:
            home_stats_obj = get_stats_block(home_bs, home_score, away_score)
            away_stats_obj = get_stats_block(away_bs, away_score, home_score)
        except Exception as e:
            print(f"  ⚠️ Error parsing stats for {game_id}: {e}")
            continue

        # Construct Schema Object
        game_obj = {
            "game_id": f"{date_str_file}-{home_abbr}-{away_abbr}",
            "date": date_str_file,
            "teams": {
                "home": home_abbr,
                "away": away_abbr
            },
            "home_stats": home_stats_obj,
            "away_stats": away_stats_obj,
            "market_line": market_line
        }
        
        daily_games.append(game_obj)

    # 3. Save to File
    if daily_games:
        out_path = os.path.join(OUTPUT_DIR, f"{date_str_file}.json")
        with open(out_path, "w") as f:
            json.dump({"games": daily_games}, f, indent=2)
        print(f"  ✅ Saved {len(daily_games)} games to {out_path}")
    else:
        print(f"  ℹ️ No games found/processed for {date_str_file}")

def main():
    ensure_dir(OUTPUT_DIR)
    
    current = START_DATE
    while current <= END_DATE:
        process_date(current)
        current += timedelta(days=1)
        # Be nice to API between days
        time.sleep(0.5)

if __name__ == "__main__":
    main()
