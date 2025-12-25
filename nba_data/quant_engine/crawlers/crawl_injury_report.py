import requests
import json
import os
import datetime
import time

# Configuration
RAW_INJURY_DIR = "raw/injury"
os.makedirs(RAW_INJURY_DIR, exist_ok=True)

# ESPN Team IDs (1 to 30 roughly, but some gaps/offsets? Best to use a known list or just 1-35 range safely)
# Standard NBA Team IDs in ESPN: 1..30 (Lakers=13, etc.)
TEAM_IDS = range(1, 31) 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def fetch_espn_injuries():
    print("🚑 Fetching Injuries via ESPN Roster API...")
    all_injuries = []
    
    for team_id in TEAM_IDS:
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
        try:
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                team_name = data.get('team', {}).get('displayName', f"Team {team_id}")
                athletes = data.get('athletes', [])
                
                # Check for injuries
                for player in athletes:
                    injuries = player.get('injuries', [])
                    if injuries:
                        # Player has injury data
                        player_name = player.get('displayName')
                        for inj in injuries:
                            all_injuries.append({
                                "team": team_name,
                                "team_id": team_id,
                                "player": player_name,
                                "player_id": player.get('id'),
                                "status": inj.get('status'),
                                "date": inj.get('date'),
                                "type": inj.get('type'),
                                "details": inj.get('details', {}).get('returnDate')
                            })
            else:
                print(f"⚠️ Failed to fetch Team {team_id}: {resp.status_code}")
                
            time.sleep(0.2) # Polite delay
            
        except Exception as e:
            print(f"❌ Error fetching Team {team_id}: {e}")

    # Save
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    filepath = os.path.join(RAW_INJURY_DIR, f"{today_str}_espn_injuries.json")
    
    with open(filepath, "w") as f:
        json.dump(all_injuries, f, indent=2)
        
    print(f"✅ Saved {len(all_injuries)} injury records to {filepath}")

if __name__ == "__main__":
    fetch_espn_injuries()
