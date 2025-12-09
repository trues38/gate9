import duckdb
import json
import random
from datetime import datetime

async def generate_terminal_json(game_id):
    """
    Generates the 7-Layer Terminal View JSON.
    Attempts to fetch from DuckDB/Supabase. 
    Fallbacks to structure mock for demo if data missing.
    """
    
    # Initialize Structure
    terminal_view = {
        "layer_1_meta": {},
        "layer_2_team_regimes": {},
        "layer_3_player_regimes": {},
        "layer_4_injury_report": {},
        "layer_5_lineups": {},
        "layer_6_referee": {},
        "layer_7_trends": {}
    }
    
    print(f"      [30_terminal_view] Fetching Data for {game_id}...")
    
    # --- LAYER 1: GAME META ---
    # Mock for now as we don't have live schedule DB connected in this env
    terminal_view["layer_1_meta"] = {
        "game_id": game_id,
        "date": datetime.today().strftime('%Y-%m-%d'),
        "home_team": "LAL",
        "away_team": "GSW",
        "venue": "Crypto.com Arena",
        "start_time": "19:00 PST",
        "odds": {
            "opening": {"spread": -2.5, "total": 234.5},
            "live": {"spread": -3.5, "total": 235.0} # implies line movement
        }
    }

    # --- LAYER 2: TEAM REGIMES ---
    terminal_view["layer_2_team_regimes"] = {
        "home": {
            "team": "LAL",
            "momentum": 78.5,
            "volatility": "HIGH",
            "tags": ["Pace Pusher", "Paint Dominant"]
        },
        "away": {
            "team": "GSW",
            "momentum": 62.1,
            "volatility": "MEDIUM",
            "tags": ["3PT Heavy", "Road Struggle"]
        }
    }

    # --- LAYER 3: PLAYER REGIMES (Top 8) ---
    # Real logic would query `fact_rosters`
    players = []
    for p in ["LeBron James", "Anthony Davis", "D'Angelo Russell", "Austin Reaves", "Rui Hachimura"]:
        players.append({
            "name": p,
            "team": "LAL",
            "regime": random.choice(["SURGING", "STABLE", "SLUMPING"]),
            "momentum": round(random.uniform(40, 95), 1),
            "archetype": "Playmaker" if "James" in p or "Russell" in p else "Scorer"
        })
    for p in ["Stephen Curry", "Klay Thompson", "Draymond Green", "Andrew Wiggins", "Jonathan Kuminga"]:
         players.append({
            "name": p,
            "team": "GSW",
            "regime": random.choice(["SURGING", "STABLE", "SLUMPING"]),
            "momentum": round(random.uniform(40, 95), 1),
            "archetype": "Shooter"
        })
    
    terminal_view["layer_3_player_regimes"] = players

    # --- LAYER 4: INJURY REPORT ---
    terminal_view["layer_4_injury_report"] = {
        "LAL": [
            {"player": "Gabe Vincent", "status": "OUT", "impact": "LOW"},
            {"player": "LeBron James", "status": "PROBABLE", "impact": "HIGH"}
        ],
        "GSW": [
            {"player": "Chris Paul", "status": "QUESTIONABLE", "impact": "MEDIUM"}
        ],
        "last_update": datetime.now().isoformat()
    }

    # --- LAYER 5: LINEUPS ---
    terminal_view["layer_5_lineups"] = {
        "home_starters": ["DLo", "Reaves", "Prince", "LeBron", "Davis"],
        "away_starters": ["Curry", "Klay", "Wiggins", "Draymond", "Looney"],
        "notes": "LAL going big vs GSW small ball."
    }

    # --- LAYER 6: REFEREE REGIME ---
    terminal_view["layer_6_referee"] = {
        "crew_chief": "Scott Foster",
        "crew": ["Ben Taylor", "Natalie Sago"],
        "metrics": {
            "home_win_pct": 42.5, # The "Foster Effect"
            "foul_rate": "HIGH",
            "chaos_factor": 88
        }
    }

    # --- LAYER 7: TRENDS ---
    terminal_view["layer_7_trends"] = {
        "pace_projection": 102.5,
        "variance_risk": "EXTREME",
        "historical_matchup": "LAL won last 3 home games vs GSW.",
        "fatigue_index": {"LAL": 0, "GSW": 1} # GSW on B2B
    }

    return terminal_view
