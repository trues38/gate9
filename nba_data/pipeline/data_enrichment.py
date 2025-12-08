import requests
import json
import os
import random

# CONFIG
DATA_DIR = "nba_data/enrichment"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. REFEREE REGIME (The "Secret Weapon")
# ---------------------------------------------------------
class RefereeRegime:
    def __init__(self):
        # V1: Static Knowledge Base (The "Known" Quantities)
        # In V2, we scrape official.nba.com/referee-assignments/
        self.ref_db = {
            "Scott Foster": {
                "style": "Control Enforcer",
                "home_win_pct": 61,
                "foul_rate": "High",
                "variance_impact": "Suppressor", # Kills chaos
                "pace_impact": "Slow"
            },
            "Zach Zarba": {
                "style": "Let-them-play",
                "home_win_pct": 49,
                "foul_rate": "Low",
                "variance_impact": "Amplifier", # Allows runs
                "pace_impact": "Fast"
            },
            "Tony Brothers": {
                "style": "Volatile Interventionist",
                "home_win_pct": 55,
                "foul_rate": "High",
                "variance_impact": "Chaos Generator",
                "pace_impact": "Mixed"
            },
            "Bill Kennedy": {
                "style": "Fair & Balanced",
                "home_win_pct": 52,
                "foul_rate": "Medium",
                "variance_impact": "Neutral",
                "pace_impact": "Neutral"
            }
        }

    def get_assignment(self, game_id):
        # Mock Assessment for Demo (Since scraping requires day-of exact matching)
        # Randomly assign 3 refs from pool + generics
        crew_chief = random.choice(list(self.ref_db.keys()))
        return {
            "crew_chief": crew_chief,
            "regime": self.ref_db.get(crew_chief)
        }

# ---------------------------------------------------------
# 2. ESPN ZERO-COST ENRICHER (Injuries, Lineups)
# ---------------------------------------------------------
class ESPNEnricher:
    def __init__(self):
        self.base_url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

    def fetch_game_data(self, game_id):
        # We fetch the scoreboard and filter for the game_id
        # This endpoint contains deep nested data
        try:
            resp = requests.get(self.base_url, timeout=10)
            data = resp.json()
            
            # Find the specific game
            target_event = None
            for event in data.get('events', []):
                if event.get('id') == str(game_id):
                    target_event = event
                    break
            
            if not target_event:
                # Fallback: Try specific summary endpoint if scoreboard doesn't cover it
                return self.fetch_summary(game_id)
                
            return self.parse_event(target_event)
            
        except Exception as e:
            print(f"❌ ESPN Fetch Error: {e}")
            return None

    def fetch_summary(self, game_id):
        # Detailed game summary endpoint
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            # This mimics the event structure roughly
            return self.parse_summary(data)
        except Exception as e:
            print(f"❌ Summary Fetch Error: {e}")
            return None

    def parse_summary(self, data):
        # DEBUG: Inspect Keys
        # print("KEYS:", data.keys())
        # if 'pickcenter' in data: print("PICKCENTER:", data['pickcenter'])
        # if 'injuries' in data: print("INJURIES FOUND")
        
        # Extract Injuries & Lineups from Summary JSON
        output = {
            "injuries": {"home": [], "away": []},
            "odds": {}
        }
        
        # 1. Prediction / Odds
        if 'pickcenter' in data:
            pc = data['pickcenter']
            if pc:
                primary = pc[0]
                output['odds'] = {
                    "provider": primary.get('provider', {}).get('name'),
                    "details": primary.get('details'), # e.g. "BOS -6.5"
                    "overUnder": primary.get('overUnder')
                }

        # 2. Injuries extraction logic (attempt to find path)
        # Often in data['boxscore']['teams'][i]['team']['injuries'] ??
        # Or data['injuries'] ??
        
    def fetch_roster(self, team_id):
        # Specific Roster Endpoint for accurate Injury Data
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            data = resp.json()
            
            full_roster = []
            injuries = []
            
            # Iterate athletes
            for section in data.get('athletes', []):
                for player in section.get('items', []):
                    name = player.get('fullName')
                    if name:
                        full_roster.append(name)

                    # Check 'injuries' array
                    if player.get('injuries'):
                        for inj in player['injuries']:
                            injuries.append({
                                "player": name,
                                "status": inj.get('status', 'Unknown'),
                                "description": inj.get('longComment', 'Undisclosed')
                            })
                            
            return injuries, full_roster
        except Exception as e:
            print(f"❌ Roster Fetch Error (Team {team_id}): {e}")
            return [], []
        except Exception as e:
            print(f"❌ Roster Fetch Error (Team {team_id}): {e}")
            return []

    def parse_summary(self, data):
        output = {
            "odds": {}
        }
        
        # 1. Prediction / Odds
        if 'pickcenter' in data:
            pc = data['pickcenter']
            if pc:
                primary = pc[0]
                output['odds'] = {
                    "provider": primary.get('provider', {}).get('name'),
                    "details": primary.get('details'), # e.g. "BOS -6.5"
                    "overUnder": primary.get('overUnder')
                }
        return output

# ---------------------------------------------------------
# MAIN ORCHESTRATOR
# ---------------------------------------------------------
def enrich_game(game_id, home_id, away_id):
    print(f"🕵️ Enriched Intelligence Running for Game {game_id}...")
    
    # 1. Referees
    ref_engine = RefereeRegime()
    ref_data = ref_engine.get_assignment(game_id)
    print(f"   🦓 Referee Regime: {ref_data['crew_chief']} ({ref_data['regime']['style']})")
    
    # 2. ESPN Data (Odds from Summary)
    espn = ESPNEnricher()
    summary_data = espn.fetch_summary(game_id)
    odds = {}
    if summary_data:
        odds = summary_data.get('odds', {})
        print(f"   📡 Market Data: {odds}")
    else:
        print("   ⚠️ Market Data Unavailable (API Error)")
    
    # 3. Injuries & Rosters (From Roster Endpoints)
    print(f"   🚑 Fetching Roster Health (Home: {home_id}, Away: {away_id})...")
    home_injuries, home_roster = espn.fetch_roster(home_id)
    away_injuries, away_roster = espn.fetch_roster(away_id)
    
    # 4. Combine
    enriched = {
        "game_id": game_id,
        "home_id": home_id,
        "away_id": away_id,
        "referee_context": ref_data,
        "market_context": odds,
        "injury_context": {
            "home": home_injuries,
            "away": away_injuries
        },
        "rosters": {
             "home": home_roster,
             "away": away_roster
        }
    }
    
    # Save
    fname = os.path.join(DATA_DIR, f"enriched_{game_id}.json")
    with open(fname, 'w') as f:
        json.dump(enriched, f, indent=2)
        
    print(f"✅ Enrichment Complete: {fname}")
    return enriched

if __name__ == "__main__":
    # Test with BOS (2) vs TOR (28)
    enrich_game("401810213", 28, 2)
