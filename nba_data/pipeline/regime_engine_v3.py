
import duckdb
import pandas as pd
import numpy as np
from datetime import date, datetime
import json
import glob
import os
from openai import OpenAI
from dotenv import load_dotenv

# CONFIG
DB_PATH = "nba_analytics.duckdb"
SNAPSHOT_DIR = "nba_data/snapshots"
load_dotenv("/Users/js/g9/.env")

STARS = [
    # TOR/NYK
    "Scottie Barnes", "RJ Barrett", "Immanuel Quickley", "Gradey Dick", "Jakob Poeltl",
    "Jalen Brunson", "Karl-Anthony Towns", "Mikal Bridges", "OG Anunoby", "Josh Hart",
    # MIA/ORL
    "Jimmy Butler", "Bam Adebayo", "Tyler Herro", "Terry Rozier", "Jaime Jaquez Jr.",
    "Paolo Banchero", "Franz Wagner", "Jalen Suggs", "Wendell Carter Jr.", "Cole Anthony",
    # LEAGUE WIDE (Partial List)
    "LeBron James", "Anthony Davis", "Stephen Curry", "Luka Doncic", "Kyrie Irving",
    "Nikola Jokic", "Jamal Murray", "Shai Gilgeous-Alexander", "Chet Holmgren",
    "Kevin Durant", "Devin Booker", "Anthony Edwards", "Rudy Gobert", "Victor Wembanyama",
    "Jayson Tatum", "Jaylen Brown", "Giannis Antetokounmpo", "Damian Lillard",
    "Joel Embiid", "Tyrese Maxey", "Donovan Mitchell", "Trae Young"
]

DEFAULT_REFS = {
    "Josh Tiven": {"pace": -1.2, "style": "Pace Suppressor"},
    "Jacyn Goble": {"pace": 0.0, "style": "Neutral"},
    "Brandon Adair": {"pace": -0.5, "style": "Standard"}, 
    "Scott Foster": {"pace": -2.0, "style": "Control Enforcer"}
}

def get_latest_story(team_keyword):
    keywords = [team_keyword]
    if team_keyword == "MIA": keywords = ["Miami", "Heat"]
    if team_keyword == "ORL": keywords = ["Orlando", "Magic"]
    if team_keyword == "TOR": keywords = ["Toronto", "Raptors"]
    if team_keyword == "NYK": keywords = ["New York", "Knicks"]
    
    files = sorted(glob.glob("nba_data/stories_raw/*.json"), key=os.path.getmtime, reverse=True)
    for fpath in files[:200]: 
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                body = data.get("body", "")
                for k in keywords:
                    if k in body:
                        return body[:300] + "..." 
        except: 
            continue
    return "No recent narrative found."

def build_game_object(game_id, home_id, away_id, home_abbr, away_abbr, referee_override=None):
    """
    Constructs the Unified GameObject (JSON)
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    today_str = str(date.today())
    
    # 1. Team Regimes
    def get_team_regime(tid):
        q = f"SELECT momentum_score, volatility_score, regime_label FROM fact_regimes WHERE team_id={tid} ORDER BY date DESC LIMIT 1"
        res = con.sql(q).fetchone()
        if res: return {"momentum": float(res[0]), "volatility": float(res[1]), "label": res[2]}
        return {"momentum": 0.0, "volatility": 0.0, "label": "Unknown"}
        
    h_reg = get_team_regime(home_id)
    a_reg = get_team_regime(away_id)
    
    # 2. Player Regimes (Filtered by Injuries)
    # Check Injuries First
    def get_injuries(tid):
        try:
            q = f"SELECT player_name, status FROM fact_injuries WHERE team_id={tid} AND status='Out'"
            return [r[0] for r in con.sql(q).fetchall()]
        except: return []
    
    h_out = get_injuries(home_id)
    a_out = get_injuries(away_id)
    
    def get_players(tid, out_list):
        q = f"""
        SELECT r.name, pr.momentum_score, pr.volatility_score
        FROM fact_rosters r
        JOIN fact_player_regimes pr ON r.player_id = pr.player_id
        WHERE r.team_id = {tid}
        """
        all_p = con.sql(q).fetchall()
        valid = []
        for p in all_p:
            name, mom, vol = p
            if name in out_list: continue # Filter Out
            
            is_star = any(s in name for s in STARS)
            impact = round(mom * 1.2, 2)
            valid.append({
                "name": name, "momentum": mom, "volatility": vol, 
                "impact": impact, "is_star": is_star,
                "score": abs(impact) + (5.0 if is_star else 0)
            })
        valid.sort(key=lambda x: x['score'], reverse=True)
        return valid[:4] # Top 4
        
    h_players = get_players(home_id, h_out)
    a_players = get_players(away_id, a_out)
    
    # 3. Referees
    refs = []
    if referee_override:
        # User provided list of names
        for r_name in referee_override:
            # Lookup default stats or assume Neutral/Standard if unknown
            s = DEFAULT_REFS.get(r_name, {"pace": 0.0, "style": "Standard"})
            refs.append({"name": r_name, "pace": s['pace'], "weight": 0.33})
    else:
        # Mock Selection (Fallback)
        refs = [
            {"name": "Josh Tiven", "pace": -1.2, "weight": 0.5},
            {"name": "Jacyn Goble", "pace": 0.0, "weight": 0.3},
            {"name": "Brandon Adair", "pace": -0.5, "weight": 0.2}
        ]
    
    # 4. Narratives
    h_news = get_latest_story(home_abbr)
    a_news = get_latest_story(away_abbr)
    
    # 5. Actual Result (If exists)
    actual = None
    try:
        res = con.execute(f"SELECT * FROM fact_game_results WHERE game_id='{game_id}'").fetchone()
        if res:
            actual = {
                "home_score": res[4], "away_score": res[5],
                "spread_line": res[6], "total_line": res[7]
            }
    except: pass
        
    con.close()
    
    today_date = date.today()
    
    # Construct Object
    game_obj = {
        "game_id": game_id,
        "freeze_time_kst": "17:00 KST", # HARDCODED PROTOCOL TIME
        "timestamp": datetime.now().isoformat(),
        "teams": {"home": home_abbr, "away": away_abbr},
        "team_ids": {"home": home_id, "away": away_id},
        "team_regimes": {home_abbr: h_reg, away_abbr: a_reg},
        "player_regimes": {home_abbr: h_players, away_abbr: a_players},
        "referees": refs,
        "injuries": {home_abbr: h_out, away_abbr: a_out},
        "news_narrative": {home_abbr: h_news, away_abbr: a_news},
        "actual_game_result": actual
    }
    return game_obj

def analyze_from_snapshot(snapshot_path):
    """
    Reads JSON Snapshot -> Generates 11-Layer Report via LLM
    """
    with open(snapshot_path, "r") as f:
        data = json.load(f)
        
    print(f"🧠 Analysis Engine V3: Reading Snapshot {snapshot_path}...")
    
    # Quant Logic (Layers 1-4 Calculation locally)
    # L4 Market Model
    hmom = data['team_regimes'][data['teams']['home']]['momentum']
    amom = data['team_regimes'][data['teams']['away']]['momentum']
    
    # Base Model
    spread_model = 2.5 + ((hmom - amom) * 5.0)
    
    # Injury Penalties
    h_inj_count = 0
    a_inj_count = 0 
    h_out = data['injuries'][data['teams']['home']]
    a_out = data['injuries'][data['teams']['away']]
    
    h_star_loss = sum([1 for p in h_out if any(s in p for s in STARS)])
    a_star_loss = sum([1 for p in a_out if any(s in p for s in STARS)])
    
    spread_model -= (h_star_loss * 2.0)
    spread_model += (a_star_loss * 2.0)
    
    # Referee Adjustment (New V3 Logic)
    ref_pace_sum = sum([r['pace'] for r in data['referees']])
    
    fair_margin = round(spread_model, 1)
    
    # Prepare Context for LLM
    context = f"""
    [UNIFIED GAME OBJECT SNAPSHOT]
    Teams: {data['teams']['away']} @ {data['teams']['home']}
    Snapshot Freeze Time: {data.get('freeze_time_kst', 'Unknown')}
    (NOTE: Injuries/Lineups after this time are NOT included.)
    
    [TEAM REGIMES]
    {data['teams']['home']}: {data['team_regimes'][data['teams']['home']]}
    {data['teams']['away']}: {data['team_regimes'][data['teams']['away']]}
    
    [PLAYER X-DNA (Active Top 4)]
    {data['teams']['home']}: {data['player_regimes'][data['teams']['home']]}
    {data['teams']['away']}: {data['player_regimes'][data['teams']['away']]}
    
    [INJURY REPORT (Excluded)]
    {data['teams']['home']} Out: {h_out} (Star Loss: {h_star_loss})
    {data['teams']['away']} Out: {a_out} (Star Loss: {a_star_loss})
    
    [REFEREES]
    {data['referees']} (Net Pace Impact: {ref_pace_sum:.1f}%)
    
    [NARRATIVES]
    {data['news_narrative']}
    
    [QUANT MODEL LEAN]
    Fair Spread: {data['teams']['home']} by {fair_margin}
    """
    
    system_prompt = """
    You are 'Pro-Analyst' running on Regime Zero V3 Engine.
    Use the provided JSON Snapshot Data to write a "High-End Analyst Report".
    
    CRITICAL INSTRUCTIONS:
    1. **Consistency**: Use ONLY the data provided. Do not hallucinate external stats.
    2. **Language**: Korean (한국어).
    3. **Structure**: 11-Layer Markdown Format.
    4. **Verdict**: Be decisive based on the Model Lean vs Market.
    5. **Disclaimer**: MUST include "[Notice] Data Frozen at 17:00 KST. Late updates not included."
    """
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ]
        )
        report = completion.choices[0].message.content
        
        # Save Report
        out_name = snapshot_path.replace(".json", "_report.md")
        with open(out_name, "w") as f:
            f.write(report)
        print(f"✅ Report Saved: {out_name}")
        
    except Exception as e:
        print(f"❌ LLM Error: {e}")

def run_pipeline_v3(home_id, away_id, home_abbr, away_abbr, game_id_override=None, referee_override=None):
    gid = game_id_override or f"{date.today()}_{home_abbr}_{away_abbr}"
    
    # 1. Build & Save Snapshot
    print(f"📸 Building Snapshot for {gid}...")
    obj = build_game_object(gid, home_id, away_id, home_abbr, away_abbr, referee_override)
    
    path = f"{SNAPSHOT_DIR}/snapshot_{gid}.json"
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"✅ Snapshot Frozen: {path}")
    
    # 2. Run Analysis from Snapshot
    analyze_from_snapshot(path)

if __name__ == "__main__":
    # BLIND TEST: ORL @ MIA
    # USER SPECIFIED REFS: COURTNEY KIRKLAND, TRE MADDOX, ROBERT HUSSEY
    my_refs = ["Courtney Kirkland", "Tre Maddox", "Robert Hussey"]
    run_pipeline_v3(14, 19, "MIA", "ORL", 
                    game_id_override="2025-12-10_MIA_ORL",
                    referee_override=my_refs)
