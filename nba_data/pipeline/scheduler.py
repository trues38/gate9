import requests
import json
import datetime

def get_schedule(date_str):
    print(f"📅 Checking Schedule for: {date_str}")
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        events = data.get('events', [])
        print(f"   Found {len(events)} games.")
        
        for event in events:
            game_id = event['id']
            status = event['status']['type']['state'] # pre, in, post
            score_summary = "vs"
            
            competitors = event['competitions'][0]['competitors']
            home = next(c for c in competitors if c['homeAway'] == 'home')
            away = next(c for c in competitors if c['homeAway'] == 'away')
            
            if status == 'post':
                score_summary = f"{away['score']} - {home['score']}"
                winner = away['team']['displayName'] if int(away['score']) > int(home['score']) else home['team']['displayName']
                print(f"   ✅ [FINAL] {away['team']['displayName']} @ {home['team']['displayName']} ({score_summary}) -> Winner: {winner}")
            else:
                print(f"   ⏰ [PREVIEW] {away['team']['displayName']} @ {home['team']['displayName']} (ID: {game_id})")
                
        return events
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def run_demo():
    # 1. Today (Dec 7) - Checking if we can see results (Simulating 'Evening Update')
    # Note: In real time it might be early, so they might be Preview.
    today = "20251207" 
    get_schedule(today)

    # 2. Tomorrow (Dec 8) - Checking Future IDs
    tomorrow = "20251208"
    get_schedule(tomorrow)

if __name__ == "__main__":
    run_demo()
