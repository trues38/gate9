
import requests
import json
import time

# Based on ESPN V2 Teams
ALL_TEAM_IDS = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30
]

def fetch_active_roster(team_id):
    # 1. Schedule -> Last Game
    try:
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        
        events = data.get('events', [])
        completed = [e for e in events if e.get('competitions', [{}])[0].get('status', {}).get('type', {}).get('name') == 'STATUS_FINAL']
        
        if not completed:
            return []
            
        completed.sort(key=lambda x: x['date'])
        last_game = completed[-1]
        last_game_id = last_game['id']
        
    except Exception:
        return []

    # 2. Summary -> Boxscore
    try:
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={last_game_id}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        
        box = data.get('boxscore', {})
        teams = box.get('teams', [])
        
        my_players = []
        for t in teams:
            if str(t.get('team', {}).get('id')) == str(team_id):
                # players are in 'statistics' -> [0] -> 'athletes' usually?
                # Wait, structure varies. 'players' key exists in V2 boxscore.
                pass
                
        # Retry finding 'boxscore' -> 'players' if 'teams' fails to yield lists
        # ESPN V2 structure is tricky. Let's use the list present in 'boxscore'['players'] if available
        # But 'summary' endpoint puts players in boxscore->teams->[i]->statistics->athletes NOT reliably.
        # SAFE BET: 'boxscore' -> 'players' -> [i] -> 'team' -> 'athletes' ? 
        # based on prototype log: 'Boxscore found in Summary'.
        
        # Let's use generic parsing
        all_athletes = []
        
        # Method A: Top-level players list
        if 'players' in box:
            for section in box['players']:
                if str(section.get('team', {}).get('id')) == str(team_id):
                    all_athletes = section.get('statistics', [{}])[0].get('athletes', [])
                    break
                    
        roster = []
        for p in all_athletes:
            name = p.get('athlete', {}).get('displayName')
            if name:
                # Add metadata
                starter = p.get('starter', False)
                # Parse stats for momentum?
                stats = p.get('stats', [])
                pts = 0
                try:
                    pts = int(stats[-1]) # Points usually last
                except:
                    pass
                
                roster.append({
                    "name": name,
                    "team_id": team_id,
                    "starter": starter,
                    "last_pts": pts,
                    "regime": {
                        "momentum_score": 1.0 + (pts/20.0) if pts > 15 else 0.8 # Simple momentum proxy
                    }
                })
                
        return roster
        
    except Exception:
        return []

def update_all_rosters():
    print("🚀 Syncing GLOBAL ROSTERS from Live Boxscores...")
    
    master_roster = []
    
    for tid in ALL_TEAM_IDS:
        print(f"   Fetching Team {tid}...", end="\r")
        r = fetch_active_roster(tid)
        if r:
            master_roster.extend(r)
        time.sleep(0.2)
        
    print(f"\n✅ Synced {len(master_roster)} active players.")
    
    # Save to current_regimes.json (This replaces the old mock file)
    with open("nba_data/regimes/current_regimes.json", "w") as f:
        json.dump(master_roster, f, indent=2)
        
    print("💾 Saved to nba_data/regimes/current_regimes.json")

if __name__ == "__main__":
    update_all_rosters()
