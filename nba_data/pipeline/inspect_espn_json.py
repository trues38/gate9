
import requests
import json
from datetime import date

def run_debug():
    # Use a well-known recent game or fetch one
    # Fetching a game from a specific date ensures we have data
    url_sb = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20240212" # A date with games
    try:
        data = requests.get(url_sb, timeout=10).json()
        gid = data['events'][0]['id']
        print(f"Inspecting Game {gid}...")
        
        url_box = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid}"
        summary = requests.get(url_box, timeout=10).json()
        
        # 1. Inspect Team Statistics in Boxscore
        if 'boxscore' in summary and 'teams' in summary['boxscore']:
            print("\n--- Boxscore Team Stats ---")
            for team in summary['boxscore']['teams']:
                print(f"Team: {team['team']['displayName']}")
                # Usually statistics are in a list
                for stat_group in team.get('statistics', []):
                    print(f"  Group: {stat_group.get('name')}")
                    print(f"  Labels: {stat_group.get('names')}")
                    print(f"  Values: {stat_group.get('displayValue')}") # Sometimes it's 'descriptions' or 'labels'
                    
                    # Check text labels for 'pace' or 'poss'
                    for label in stat_group.get('labels', []):
                         if 'poss' in label.lower() or 'pace' in label.lower():
                             print(f"  !!! FOUND MATCH: {label}")

        # 2. Inspect Header/Competitions (sometimes has record or extra stats)
        if 'header' in summary:
            print("\n--- Header Stats ---")
            for comp in summary['header']['competitions']:
                for competitor in comp['competitors']:
                    print(f"Competitor: {competitor['team']['displayName']}")
                    if 'statistics' in competitor:
                         print(f"  Stats: {competitor['statistics']}") # often just records
        
        # 3. Check for 'predictor' or 'analytics' fields
        if 'predictor' in summary:
             print("\n--- Predictor ---")
             print(summary['predictor'])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_debug()
