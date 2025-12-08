import requests
import json
import os
import sys

# Import Pipeline Steps
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_enrichment import enrich_game
from unified_report_v2 import generate_report

# CONFIG
DATE = "20251208"

def run_batch():
    print(f"🚀 Starting Batch Processing for {DATE}...")
    
    # 1. Fetch Scoreboard to get Game Metadata
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={DATE}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ Scoreboard Fetch Failed: {e}")
        return

    games = []
    for event in data.get('events', []):
        game_id = event['id']
        competitions = event['competitions'][0]
        
        # Extract Team IDs
        home_team = next(c for c in competitions['competitors'] if c['homeAway'] == 'home')
        away_team = next(c for c in competitions['competitors'] if c['homeAway'] == 'away')
        
        games.append({
            "id": game_id,
            "home_id": home_team['id'],
            "home_name": home_team['team']['displayName'],
            "away_id": away_team['id'],
            "away_name": away_team['team']['displayName']
        })

    print(f"📋 Found {len(games)} games.")

    # 2. Process Each Game
    generated_reports = []
    for game in games:
        print(f"\n⚙️ Processing {game['away_name']} @ {game['home_name']} ({game['id']})...")
        
        # Step 1: Enrich Data
        try:
            enrich_game(game['id'], game['home_id'], game['away_id'])
        except Exception as e:
            print(f"  ⚠️ Enrichment Warning: {e}")
            
        # Step 2: Generate Report (with Fallback)
        try:
            generate_report(game['id'])
            generated_reports.append(game)
        except Exception as e:
            print(f"  ❌ Generation Failed: {e}")

    # 3. Update Dashboard JSON (Optional stub for frontend)
    save_dashboard_data(generated_reports)

def save_dashboard_data(games):
    path = "web/public/data/dashboard.json"
    with open(path, "w") as f:
        json.dump(games, f, indent=2)
    print(f"✅ Dashboard Data Updated: {path}")

if __name__ == "__main__":
    run_batch()
