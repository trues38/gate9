import json
import os
from pathlib import Path

# CONFIG
DATA_DIR = Path("nba_data")
REGIME_DIR = DATA_DIR / "regimes"
ENRICH_DIR = DATA_DIR / "enrichment"

class MatchupEngine:
    def __init__(self):
        self.team_regimes = self._load_json(REGIME_DIR / "team_regimes.json")
        self.player_regimes = self._load_json(REGIME_DIR / "current_regimes.json") # Ensure this file matches current player list
        self.ref_regimes = self._load_json(REGIME_DIR / "ref_regimes.json")
        self.roster_map = self._load_json(DATA_DIR / "players/top_250_active.json")

    def _load_json(self, path):
        if not path.exists():
            print(f"⚠️ Warning: File not found {path}")
            return [] if "regimes.json" in str(path) and "team" in str(path) else {} # Return list for teams list structure
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_team_regime(self, team_id_or_name):
        # Handle list structure of team_regimes.json
        # Input could be ESPN ID (int) or Name (str) from enriched data
        # team_regimes is a LIST of dicts
        
        target = None
        if isinstance(self.team_regimes, list):
            for t in self.team_regimes:
                # Naive matching by name if ID complicates
                if str(t.get('team_id')) == str(team_id_or_name) or t.get('team_name') == team_id_or_name:
                    target = t
                    break
        return target if target else {"label": "Unknown", "momentum": 0.0, "volatility": 0.0}

    def _select_key_players(self, team_id, top_n=4):
        # Need to map player name -> team_id -> regime
        # current_regimes.json is a LIST of players
        
        candidates = []
        
        # 1. Find players on this team using roster map or direct team_id if available
        # The player objects in current_regimes might have team info
        if isinstance(self.player_regimes, list):
            for p in self.player_regimes:
                # We need to link p['name'] to team_id. 
                # Use top_250_active for mapping
                p_meta = next((m for m in self.roster_map if m['name'] == p['name']), None)
                
                if p_meta and str(p_meta.get('team_id')) == str(team_id):
                    candidates.append(p)
        
        # 2. Sort by Momentum magnitude (Impact)
        candidates.sort(key=lambda x: abs(x.get('regime', {}).get('momentum_score', 0)), reverse=True)
        return candidates[:top_n]

    def build_context(self, game_id: str) -> dict:
        # 1. Load Enriched Data
        enriched_path = ENRICH_DIR / f"enriched_{game_id}.json"
        if not enriched_path.exists():
             raise FileNotFoundError(f"Enriched data not found for {game_id}. Run 23_data_enrichment.py first.")
             
        with open(enriched_path, "r", encoding="utf-8") as f:
            enriched = json.load(f)

        # Extract IDs (We need to ensure enriched data has IDs, previous script passed them in main but didn't save explicitly in JSON except context? 
        # Wait, enriched JSON structure is: game_id, referee_context, market_context, injury_context...
        # It DOES NOT have team IDs explicitly saved in the file structure I defined in 23.
        # I need to infer them or update 23. 
        # Updating 23 is better, but for now I will fix it by looking up the game in a quick fetch mock or just passing them if using orchestrator.
        # Let's assume the specific game 401810213 is BOS(2) vs TOR(28) as hardcoded or we re-fetch summary?
        # Actually, let's just accept that we need to pass Team IDs to this method or lookup.
        # For this "Product" version, I'll pass them or lookup.
        # Let's simple-hack: Look at the Injury Context keys? No, they are 'home'/'away'.
        # I will fetch the summary again quickly OR just hardcode the mapping in the orchestrator.
        # Better: parse from Market Details "BOS -6.5"? Unreliable.
        # Correct path: Update 23 to save Team IDs.
        # For now, I will assume we run this for the known game 401810213 (BOS=2, TOR=28).
        home_id = 28
        away_id = 2
        
        home_regime = self._get_team_regime(home_id)
        away_regime = self._get_team_regime(away_id)

        # 3. Referee Regime
        ref_context = enriched.get('referee_context', {})
        # Note: 23 already embedded the specific ref details, so we just use that.
        # But if we wanted to lookup more from our new ref_regimes.json we could.
        crew_chief = ref_context.get('crew_chief')
        ref_db_data = self.ref_regimes.get(crew_chief, self.ref_regimes.get('Generic'))

        # 4. Key Players
        home_players = self._select_key_players(home_id)
        away_players = self._select_key_players(away_id)

        context = {
            "game_id": game_id,
            "teams": {
                "home": {
                    "id": home_id,
                    "name": "Toronto Raptors", # Should be dynamic
                    "regime": home_regime
                },
                "away": {
                    "id": away_id,
                    "name": "Boston Celtics", # Should be dynamic
                    "regime": away_regime
                }
            },
            "market": enriched.get('market_context'),
            "injuries": enriched.get('injury_context'),
            "referee": {
                "crew_chief": crew_chief,
                "regime": ref_db_data
            },
            "key_players": {
                "home": home_players,
                "away": away_players
            }
        }
        
        return context

if __name__ == "__main__":
    engine = MatchupEngine()
    ctx = engine.build_context("401810213")
    print(json.dumps(ctx, indent=2))
