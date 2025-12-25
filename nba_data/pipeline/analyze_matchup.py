
import duckdb
import os
import json
import datetime
from openai import OpenAI
import time

# Load Env Manually
try:
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val
except Exception:
    pass

# OPENROUTER SETUP
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"),
)

DB_PATH = "nba_analytics.duckdb"

def analyze_matchup(home_abbr, away_abbr):
    print(f"🚀 Analyzing {away_abbr} @ {home_abbr} ...")
    con = duckdb.connect(DB_PATH, read_only=True)
    
    # 1. TEAM REGIMES
    # Need to map Abbr to ID or query by ID if mapped. 
    # Let's hope my migration script mapped Key "TOR" -> ID.
    # Check dim_teams map first
    teams_df = con.sql(f"SELECT team_id, abbreviation FROM dim_teams WHERE abbreviation IN ('{home_abbr}', '{away_abbr}')").df()
    team_map = dict(zip(teams_df['abbreviation'], teams_df['team_id']))
    
    home_id = team_map.get(home_abbr, 0)
    away_id = team_map.get(away_abbr, 0)
    # Manually fix NYK if 0. ESPN uses 'NY' (ID 18).
    if away_abbr in ["NYK", "NY"] and (away_id == 0 or away_id is None):
        away_id = 18 # Official ESPN ID for Knicks
    if home_abbr in ["NYK", "NY"] and (home_id == 0 or home_id is None):
        home_id = 18
        
    # Manual Fix for TOR if 0
    if home_abbr == "TOR" and home_id == 0:
        home_id = 28 # Raptors ID
    if away_abbr == "TOR" and away_id == 0:
        away_id = 28
    
    print(f"   IDs: {home_abbr}={home_id}, {away_abbr}={away_id}")
    
    home_regime = con.sql(f"SELECT * FROM fact_regimes WHERE team_id = {home_id} ORDER BY date DESC LIMIT 1").df().to_dict(orient='records')
    away_regime = con.sql(f"SELECT * FROM fact_regimes WHERE team_id = {away_id} ORDER BY date DESC LIMIT 1").df().to_dict(orient='records')
    
    # 2. PLAYER DNA by Name Match
    # Using specific IDs guarantees we get the fresh roster we just repaired
    rosters = con.sql(f"SELECT name, team_id FROM fact_rosters WHERE team_id IN ({home_id}, {away_id})").df()
    
    home_names = rosters[rosters['team_id'] == home_id]['name'].tolist()
    away_names = rosters[rosters['team_id'] == away_id]['name'].tolist()
    
    # Fetch DNA for these players by NAME
    if home_names:
        clean_home = [name.replace("'", "''") for name in home_names if name]
        names_str = ",".join([f"'{n}'" for n in clean_home])
        if names_str:
            home_dna = con.sql(f"""SELECT player_name, regime_label, momentum_score, narrative FROM fact_player_regimes WHERE player_name IN ({names_str}) ORDER BY momentum_score DESC LIMIT 5""").df().to_dict(orient='records')
        else:
            home_dna = []
    else:
        home_dna = []
        
    if away_names:
        clean_away = [name.replace("'", "''") for name in away_names if name]
        names_str = ",".join([f"'{n}'" for n in clean_away])
        if names_str:
            away_dna = con.sql(f"""SELECT player_name, regime_label, momentum_score, narrative FROM fact_player_regimes WHERE player_name IN ({names_str}) ORDER BY momentum_score DESC LIMIT 5""").df().to_dict(orient='records')
        else:
            away_dna = []
    else:
            away_dna = []

    # 3. CONTEXT & ODDS
    # specific game context
    game_ctx = con.sql(f"SELECT * FROM game_schedule WHERE home_team='{home_abbr}' AND away_team='{away_abbr}' LIMIT 1").df().to_dict(orient='records')
    game_id = game_ctx[0]['game_id'] if game_ctx else None
    
    if game_id:
        odds = con.sql(f"SELECT * FROM market_odds WHERE game_id='{game_id}' ORDER BY timestamp DESC LIMIT 1").df().to_dict(orient='records')
    else:
        odds = []
        
    # 4. REFS (Specific Assignment Injection)
    # TOR vs NYK on Dec 9/10: Josh Tiven, Jacyn Goble, Brandon Adair
    if (home_abbr == "TOR" and away_abbr == "NYK") or (home_abbr == "NYK" and away_abbr == "TOR"):
         refs = [
             {"ref_name": "Josh Tiven", "role": "Crew Chief", "regime": "Check Database"},
             {"ref_name": "Jacyn Goble", "role": "Referee", "regime": "Check Database"},
             {"ref_name": "Brandon Adair", "role": "Umpire", "regime": "Check Database"}
         ]
         # Try to enrich stats from fact_ref_regimes
         enriched_refs = []
         for r in refs:
             try:
                 stat = con.sql(f"SELECT * FROM fact_ref_regimes WHERE ref_name LIKE '%{r['ref_name'].split()[-1]}%'").df().to_dict(orient='records')
                 if stat:
                     r['stats'] = stat[0]['stats']
                     r['regime'] = stat[0]['regime']
             except:
                 pass
             enriched_refs.append(r)
         refs = enriched_refs
    else:
         refs = con.sql("SELECT * FROM fact_ref_regimes LIMIT 3").df().to_dict(orient='records')
    
    con.close()
    
    # BUILD PROMPT
    data = {
        "matchup": f"{away_abbr} @ {home_abbr}",
        "home_regime": home_regime,
        "away_regime": away_regime,
        "home_dna_top5": home_dna,
        "away_dna_top5": away_dna,
        "odds": odds,
        "refs_watch": refs,
        "context": game_ctx,
        "note": "Referees are Confirmed for Dec 10."
    }
    
    print("🧠 Generating Deep Analysis...")
    prompt = f"""
    You are the REGIME PRO INTELLIGENCE ENGINE.
    Analyze this specific Matchup: {away_abbr} vs {home_abbr}.
    
    DATA PACKAGE:
    {json.dumps(data, indent=2, default=str)}
    
    TASK:
    Write a DEEP DIVE betting report in MARKDOWN.
    
    SECTIONS:
    1. ⚔️ **REGIME CLASH**: Compare Team Regimes (Momentum/Volatility). Who is the Juggernaut? Who is Collapsing?
    2. 🧬 **X-FACTOR DNA**: Pick 1 player from each team with the most interesting 'Narrative' or 'Momentum'. Explain why they decide the game.
    3. 📉 **MARKET READ**: Analyze the Odds (Spread/OverUnder). Is the line respecting the Regime?
    4. 🦓 **ZEBRA INTEL**: Mention referee tendencies if relevant.
    5. 🎯 **FINAL VERDICT**: Prediction & Confidence Score (0-100).
    
    Tone: Wall Street Analyst meets NBA Scout. Sharp, concise, no fluff.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat", # or auto
            messages=[{"role": "user", "content": prompt}]
        )
        report = response.choices[0].message.content
        
        filename = f"Matchup_{home_abbr}_{away_abbr}_{datetime.date.today()}.md"
        with open(filename, "w") as f:
            f.write(report)
        print(f"✅ Report Saved: {filename}")
        
    except Exception as e:
        print(f"❌ LLM Error: {e}")

if __name__ == "__main__":
    analyze_matchup("TOR", "NYK")
