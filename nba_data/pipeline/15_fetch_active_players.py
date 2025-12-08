import requests
import json
import os

# Constants
OUTPUT_DIR = "nba_data/players"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "top_250_active.json")

def fetch_active_players():
    print("🏀 Fetching Top 250 Active Players via GitHub (BasketballGM Roster)...")
    
    url = "https://raw.githubusercontent.com/alexnoob/BasketBall-GM-Rosters/master/2025-26.NBA.Roster.json"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        raw_players = data.get('players', [])
        print(f"   Fetched {len(raw_players)} players from Roster File.")
        
        active_candidates = []
        
        # Mapping BBGM TIDs to Real NBA Names (Approximate but close enough for Regime)
        # BBGM standard TIDs are usually alphabetical.
        # We mainly need the Player Name and ID to be consistent.
        
        for p in raw_players:
            tid = p.get('tid')
            
            # Filter active (0-29 are teams, -1 is FA, -2 retired usually)
            if tid is None or tid < 0:
                continue
            
            # Calculate Skill Score for Ranking
            # Use latest rating
            latest_rating = p.get('ratings', [{}])[-1]
            
            # Simple formula: Speed + Jump + Shooting + IQs
            # This captures the "Best" players reasonably well.
            skill_score = (
                latest_rating.get('spd', 0) + 
                latest_rating.get('jmp', 0) + 
                latest_rating.get('fg', 0) + 
                latest_rating.get('tp', 0) + 
                latest_rating.get('oiq', 0) + 
                latest_rating.get('diq', 0)
            )
            
            active_candidates.append({
                "id": p.get('srID', f"bbgm_{p.get('name')}"), # Use SportRadar ID if avail
                "name": p.get('name'),
                "position": p.get('pos'),
                "team_id": tid,
                "score": skill_score,
                "stats_ref": p.get('stats', [])
            })
            
        # Sort by Score Descending
        active_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Take Top 250
        top_250 = active_candidates[:250]
        print(f"   Filtered to Top {len(top_250)} based on Skill Rating.")
        
        # Save
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(top_250, f, indent=2)
            
        print(f"✅ Saved Top 250 Active Players to {OUTPUT_FILE}")
        return top_250

    except Exception as e:
        print(f"❌ Error fetching players: {e}")
        return []

if __name__ == "__main__":
    fetch_active_players()
