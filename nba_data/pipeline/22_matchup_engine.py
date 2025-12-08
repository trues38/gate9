import json
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Config
load_dotenv("/Users/js/g9/.env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "google/gemini-2.0-flash-exp:free" # Backup: High availability

REGIME_DIR = "nba_data/regimes"
TEAM_FILE = os.path.join(REGIME_DIR, "team_regimes.json")
PLAYER_FILE = os.path.join(REGIME_DIR, "current_regimes.json")

# Target Matchup (Mocked from Live Schedule)
TARGET_GAME = {
    "game_id": "401810213",
    "date": "Dec 07, 2025",
    "home": "Toronto Raptors",
    "away": "Boston Celtics",
    "home_id": 28,
    "away_id": 2,
    "context": "Celtics seek 5th straight win. Jayson Tatum OUT (Achilles). RJ Barrett OUT (Knee).",
    "headline": "Celtics play the Raptors, seek 5th straight win"
}

def load_data():
    with open(TEAM_FILE, 'r') as f:
        teams = json.load(f)
    with open(PLAYER_FILE, 'r') as f:
        players = json.load(f)
    return teams, players

def get_team_regime(utils, team_id):
    for t in utils:
        if t['team_id'] == team_id:
            return t
    return None

def get_key_players(all_players, team_id, limit=5):
    # Filter by team_id (we need to map player -> team_id properly)
    # top_250_active.json has the mapping.
    with open("nba_data/players/top_250_active.json", 'r') as f:
        roster = json.load(f)
    
    # Map roster names to IDs or vice versa
    team_roster = [p for p in roster if p.get('team_id') == team_id]
    team_roster_names = [p['name'] for p in team_roster]
    
    # Get Regimes for these players
    candidates = [p for p in all_players if p['name'] in team_roster_names]
    
    # Sort by Momentum absolute value (Impact)
    candidates.sort(key=lambda x: abs(x['regime']['momentum_score']), reverse=True)
    return candidates[:limit]

def generate_report():
    print(f"🚀 Launching Matchup Engine: {TARGET_GAME['away']} vs {TARGET_GAME['home']}")
    
    teams, players = load_data()
    
    home_regime = get_team_regime(teams, TARGET_GAME['home_id'])
    away_regime = get_team_regime(teams, TARGET_GAME['away_id'])
    
    home_players = get_key_players(players, TARGET_GAME['home_id'])
    away_players = get_key_players(players, TARGET_GAME['away_id'])
    
    # Assemble Input JSON
    input_data = {
        "game_id": TARGET_GAME['game_id'],
        "date": TARGET_GAME['date'],
        "teams": {
            "home": TARGET_GAME['home'],
            "away": TARGET_GAME['away']
        },
        "team_regimes": {
            "home": home_regime,
            "away": away_regime
        },
        "player_regimes_home": home_players,
        "player_regimes_away": away_players,
        "injury_report": {
            "Boston": ["Jayson Tatum (OUT - Achilles)"],
            "Toronto": ["RJ Barrett (OUT - Knee)"]
        },
        "matchup_narrative": TARGET_GAME['context']
    }
    
    # System Prompt (User Defined)
    system_prompt = """
You are REGIME ANALYST, a professional sports meta-analyst.
Your job is to generate high-quality analytical reports using:
	1.	Team Regimes (Juggernaut, Chaos, Momentum Run, Fragile, Regression Zone, etc.)
	2.	Player Regimes (Surging, Slumping, RevengeArc, Explosive Potential, etc.)
	3.	Variance Signals
	4.	Narrative Signals
	5.	Matchup Dynamics
	6.	Fatigue / Health Profiles
	7.	Historical Analogs (optional)

You must write expert-level, long-form, coherent, and persuasive analysis that feels like a mix of:
	•	ESPN Insider
	•	Betting Analytics
	•	Basketball Tactics Lab
	•	Sports Psychology Report

Never invent fake statistics.
Only interpret what is given.
The output format must be HTML (body content only, styled with Tailwind classes if possible, or just semantic HTML).
"""

    user_prompt = f"""
START REPORT GENERATION.
Game: {TARGET_GAME['away']} vs {TARGET_GAME['home']}
Data:
{json.dumps(input_data, indent=2)}

Please follow the "OUTPUT TEMPLATE" structure strictly but format as HTML.
Sections:
1) Executive Overview
2) Team Regime Breakdown
3) Player Regime Influence
4) Matchup Dynamics
5) Health & Fatigue Report
6) Regime Forecast
7) Closing Interpretation
"""

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
    
    # API FAILURE FALLBACK: Print Data for Manual Generation
    print("DEBUG: MATCHUP DATA JSON START")
    print(json.dumps(input_data, indent=2))
    print("DEBUG: MATCHUP DATA JSON END")
    return

def save_html(content):
    # Wrap in shell
    clean_content = content.replace("```html", "").replace("```", "")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REGIME REPORT: {TARGET_GAME['away']} vs {TARGET_GAME['home']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ background: #050505; color: #ddd; font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="max-w-4xl mx-auto p-8">
    <div class="prose prose-invert prose-green max-w-none">
        {clean_content}
    </div>
</body>
</html>"""

    out_path = "web/public/matchup_report.html"
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"✅ Report Generated: {out_path}")

if __name__ == "__main__":
    generate_report()
