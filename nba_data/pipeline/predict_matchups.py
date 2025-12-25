import requests
import argparse
from datetime import datetime
import duckdb
from fusion_engine_prototype import get_quant_layer, get_story_layer, get_conflict_layer

def print_team_report(header, q, s, f):
    if not q or not s:
        print(f"\n{header}: ⚠️ 데이터 부족")
        return

    # Handle Quant dict keys (predict script uses "score", "regime" vs prototype uses "momentum", "label")
    # Let's standardize to the prototype keys or map them.
    # Prototype: momentum, label
    # This script: score, regime
    
    q_score = q.get('momentum', q.get('score', 0))
    q_label = q.get('label', q.get('regime', 'Unknown'))
    
    print(f"\n{header} 분석 리포트")
    print(f"    ----------------------------------------")
    print(f"    📊 퀀트 (Quant)    | {q_score:.1f} ({q_label}) | L10: {q.get('record', '-')} | {q.get('streak', '-')}")
    
    # Story
    print(f"    🧠 스토리 (Story)  | {s.get('vibe', 'Unknown')} (점수: {s.get('score', 0):.2f})")
    if 'details' in s:
        print(f"       ↳ 주요 선수: {', '.join(s['details'])}")
        
    # Fusion
    print(f"    ⚡ 퓨전 진단       | {f.get('result', 'Unknown')}")
    print(f"    ⚠️ 리스크          | {f.get('risk', 'Unknown')}")

# Re-use the existing logic but fetch schedule from ESPN
CONN = duckdb.connect('nba_analytics.duckdb', read_only=True)

def fetch_schedule(date_str):
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str.replace('-', '')}"
    print(f"📅 Fetching Schedule from ESPN for {date_str}...")
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        games = []
        for evt in data.get('events', []):
            comp = evt['competitions'][0]
            home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
            away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
            
            # Name Cleaning
            h_name = home['team']['displayName'] # "Orlando Magic"
            a_name = away['team']['displayName']
            
            # Need Team IDs for DB Query (Quant Layer)
            # Query Dim Teams by Name or Abbr
            h_id = get_team_id(h_name, home['team']['abbreviation'])
            a_id = get_team_id(a_name, away['team']['abbreviation'])
            
            games.append({
                "home": h_name, "home_id": h_id, "home_abbr": home['team']['abbreviation'],
                "away": a_name, "away_id": a_id, "away_abbr": away['team']['abbreviation']
            })
        return games
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

def get_team_id(team_name, abbr=None):
    # Fuzzy or exact match
    try:
        # Try Abbr first (Most reliable if dim_teams.name is abbr)
        if abbr:
            res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE name = '{abbr}'").fetchone()
            if res: return res[0]
            
        # Try exact name (full_name column maybe?)
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE full_name = '{team_name}'").fetchone()
        if res: return res[0]
        
        # Try like on name
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE full_name LIKE '%{team_name.split()[-1]}%'").fetchone()
        if res: return res[0]
    except:
        pass
    return None

def analyze_preview(target_date):
    games = fetch_schedule(target_date)
    print(f"🏀 Found {len(games)} Scheduled Games for {target_date}")
    
    for g in games:
        print(f"\n==================================================")
        print(f"Matchup: {g['away']} @ {g['home']}")
        print(f"==================================================")
        
        # We need "previous" stats for prediction, so let's check stats as of TODAY (Dec 10)
        # or most recent in DB.
        # get_quant_layer queries by date. If the game hasn't happened, 
        # it won't be in fact_regimes with that date.
        # We should use the LATEST available regime for the team.
        
        # Modified Get Quant: Fetch LATEST regime
        q_home = get_latest_quant(g['home_id'])
        q_away = get_latest_quant(g['away_id'])
        
        # Get Story (Up to target date)
        # s_home = get_story_layer(g['home_id'], dt_obj) -> WRONG
        # Correct: get_story_layer(con, team_id, date_str)
        s_home = get_story_layer(CONN, g['home_id'], target_date)
        s_away = get_story_layer(CONN, g['away_id'], target_date)
        
        # Conflict
        # Debug
        print(f"DEBUG: Home Quant Keys: {q_home.keys()}")
        if 'momentum' not in q_home: print(f"DEBUG: MISSING MOMENTUM IN HOME: {q_home}")
        
        c_home = get_conflict_layer(q_home, s_home)
        c_away = get_conflict_layer(q_away, s_away)
        
        print_team_report("🏠 [홈팀] " + g['home_abbr'], q_home, s_home, c_home)
        print("")
        print_team_report("✈️  [원정팀] " + g['away_abbr'], q_away, s_away, c_away)

def get_latest_quant(team_id):
    if not team_id: return {"momentum": 0.0, "label": "Unknown", "record": "0-0", "streak": "-"}
    try:
        # Get the most recent row in fact_regimes
        q = f"""
        SELECT momentum_score, regime_label, record, streak 
        FROM fact_regimes 
        WHERE team_id={team_id} 
        ORDER BY date DESC LIMIT 1
        """
        res = CONN.sql(q).fetchone()
        if res:
            return {"momentum": float(res[0]), "label": res[1], "record": res[2], "streak": res[3]}
    except:
        pass
    return {"momentum": 0.0, "label": "No Data", "record": "0-0", "streak": "-"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    analyze_preview(args.date)
