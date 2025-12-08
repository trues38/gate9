
import requests
import json
import sys

# Test with Phoenix Suns (ID 21)
TEAM_ID = 21

def fetch_last_game_lineup(team_id):
    # 1. Fetch Schedule to find last completed game
    print(f"📅 Fetching Schedule for Team {team_id}...")
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        last_game_id = None
        last_game_date = None
        
        # Iterate events in reverse chronological order usually helps, but let's parse
        events = data.get('events', [])
        
        # Filter for 'STATUS_FINAL'
        completed = []
        for e in events:
            status = e.get('competitions', [{}])[0].get('status', {}).get('type', {}).get('name')
            if status == 'STATUS_FINAL':
                completed.append(e)
                
        if not completed:
            print("❌ No completed games found.")
            return

        # Get the most recent one (last in list usually, but sort by date to be safe)
        completed.sort(key=lambda x: x['date'])
        last_game = completed[-1]
        last_game_id = last_game['id']
        print(f"✅ Found Last Game: {last_game.get('shortName')} (Date: {last_game.get('date')}) | ID: {last_game_id}")
        
    except Exception as e:
        print(f"❌ Schedule Fetch Error: {e}")
        return

    # 2. Fetch Boxscore
    print(f"📊 Fetching Summary for Game {last_game_id}...")
    box_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={last_game_id}"
    try:
        resp = requests.get(box_url, timeout=10)
        data = resp.json()
        
        # summary often has 'boxscore' as top key
        if 'boxscore' in data:
             print("   ✅ Boxscore found in Summary")
        else:
             print(f"   ❌ Keys: {list(data.keys())}")
        
        box = data.get('boxscore', {})
        teams = box.get('teams', []) # home/away
        
        print(f"   Debug: Found {len(teams)} teams in boxscore.")
        for t in teams:
            tid = t.get('team', {}).get('id')
            print(f"   - ID Found: {tid} (Type: {type(tid)}) | Target: {team_id}")
        
        target_team = None
        for t in teams:
            if str(t.get('team', {}).get('id')) == str(team_id):
                target_team = t
                break
                
        if not target_team:
            print("❌ Team not found in boxscore.")
            return

        # 3. Extract Starters vs Bench
        # Usually players are listed. 'starter' is a boolean flag often available in detailed properties
        # OR they are just first 5.
        
        print("\n🏆 **LAST GAME ROSTER & STATS**")
        stats = target_team.get('statistics', [])
        
        # Players are usually in 'athletes' list in boxscore->teams->[i]->athletes?
        # NO, in 'boxscore'->'players' is common V2 structures
        # Let's check 'players' key in boxscore
        
        players_section = box.get('players', []) # Usually returns two lists (home/away)
        
        my_players = []
        for section in players_section:
            if str(section.get('team', {}).get('id')) == str(team_id):
                my_players = section.get('statistics', [])[0].get('athletes', []) # This might be nested
                break
                
        starters = []
        bench = []
        
        for idx, p in enumerate(my_players):
            name = p.get('athlete', {}).get('displayName')
            starter_flag = p.get('starter') # Boolean
            
            # If starter flag is missing, rely on order (first 5)
            is_starter = starter_flag if starter_flag is not None else (idx < 5)
            
            stats = p.get('stats', []) # list of strings usually
            # Pts is usually last or identifiable.
            
            p_obj = {"name": name, "starter": is_starter, "stats": stats}
            
            if is_starter:
                starters.append(p_obj)
            else:
                bench.append(p_obj)
                
        print(f"🔹 Starters ({len(starters)}):")
        for s in starters:
            print(f"   - {s['name']}")
            
        print(f"🔸 Rotation Bench ({len(bench)}):")
        for b in bench:
            # Only show if they played (did not get DNP)
            # DNP usually has fewer stat entries or 'didNotPlay' flag
            if not p.get('didNotPlay'):
               print(f"   - {b['name']}")
                
    except Exception as e:
        print(f"❌ Boxscore Fetch Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fetch_last_game_lineup(TEAM_ID)
