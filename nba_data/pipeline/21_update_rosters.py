import requests
import json
import os
import time

# Config
DATA_DIR = "nba_data/players"
OUTPUT_FILE = os.path.join(DATA_DIR, "top_250_active.json")
TEAM_REGIMES_FILE = "nba_data/regimes/team_regimes.json"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_espn_rosters():
    print("🏀 Fetching Official Rosters from ESPN API (v2 Patched)...")
    
    player_team_map = {} # "LeBron James": "Los Angeles Lakers"
    
    # We need to map ESPN Name -> Our Team Name
    # But first getting the roster is key.
    
    for team_id in range(1, 31):
        # 1. Fetch Team Meta (Name)
        meta_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}"
        team_name = None
        try:
            resp = requests.get(meta_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                team_name = data.get('team', {}).get('displayName')
        except:
            pass
            
        if not team_name:
            continue
            
        # 2. Fetch Roster
        roster_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
        try:
            print(f"   Fetching {team_name}...", end="\r")
            resp = requests.get(roster_url, timeout=5)
            if resp.status_code != 200: continue
            
            data = resp.json()
            # ROOT LEVEL ATHLETES
            athletes = data.get('athletes', [])
            
            for ath in athletes:
                name = ath.get('fullName') or ath.get('displayName')
                if name:
                    player_team_map[name] = team_name
            
            time.sleep(0.1) 
            
        except Exception as e:
            continue
            
    print(f"\n✅ Rosters Fetched. Found {len(player_team_map)} active players.")
    return player_team_map

def update_top_250():
    if not os.path.exists(OUTPUT_FILE):
        print("❌ top_250_active.json not found.")
        return

    # Load existing player data
    with open(OUTPUT_FILE, 'r') as f:
        players = json.load(f)

    # Load Team Mapping (Our System)
    if not os.path.exists(TEAM_REGIMES_FILE):
        print("❌ team_regimes.json not found. Cannot map IDs.")
        return
        
    with open(TEAM_REGIMES_FILE, 'r') as f:
        our_teams = json.load(f)
        
    # Map Our Team Name -> Our Team ID
    name_to_id = {t['team_name']: t['team_id'] for t in our_teams}
    
    # Add alias for correctness
    name_to_id["LA Clippers"] = name_to_id.get("Los Angeles Clippers")
    
    # Fetch Live Data
    real_roster_map = fetch_espn_rosters()
    
    updated_count = 0
    
    for p in players:
        p_name = p['name']
        real_team = real_roster_map.get(p_name)
        
        if real_team:
            # Check if we have an ID for this team
            new_tid = name_to_id.get(real_team)
            
            if new_tid and p.get('team_id') != new_tid:
                # print(f"   🔄 Fixed: {p_name} -> {real_team}")
                p['team_id'] = new_tid
                updated_count += 1
                
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(players, f, indent=2)
        
    print(f"✅ Roster Sync Complete. Updated {updated_count} players to 2025-26 teams.")

if __name__ == "__main__":
    update_top_250()
