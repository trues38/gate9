import argparse
import duckdb
from datetime import datetime
from fusion_engine_prototype import get_story_layer, get_conflict_layer

# Re-use logic
CONN = duckdb.connect('nba_analytics.duckdb', read_only=True)

def print_team_report(header, q, s, f):
    if not q or not s:
        print(f"\n{header}: ⚠️ 데이터 부족")
        return

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

def get_latest_quant(team_id):
    if not team_id: return {"momentum": 0.0, "label": "Unknown", "record": "0-0", "streak": "-"}
    try:
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

def get_team_id(team_name, abbr=None):
    try:
        if abbr:
            res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE name = '{abbr}'").fetchone()
            if res: return res[0]
            
        # Try exact name (Column 'abbreviation' stores the Full Name, confusingly)
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE abbreviation = '{team_name}'").fetchone()
        if res: return res[0]
        
        # Try like
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE abbreviation LIKE '%{team_name}%'").fetchone()
        if res: return res[0]
        res = CONN.sql(f"SELECT team_id FROM dim_teams WHERE name LIKE '%{team_name}%'").fetchone()
        if res: return res[0]
    except:
        pass
    return None

def simulate(home, away):
    print(f"\n🔮 Simulating Matchup: {away} @ {home}")
    
    h_id = get_team_id(home)
    a_id = get_team_id(away)
    
    if not h_id: print(f"❌ Team Not Found: {home}"); return
    if not a_id: print(f"❌ Team Not Found: {away}"); return
    
    # Use current date for Story context - ensure it catches recent stuff
    target_date = "2025-12-10" 
    
    q_home = get_latest_quant(h_id)
    q_away = get_latest_quant(a_id)
    
    s_home = get_story_layer(CONN, h_id, target_date)
    s_away = get_story_layer(CONN, a_id, target_date)
    
    c_home = get_conflict_layer(q_home, s_home)
    c_away = get_conflict_layer(q_away, s_away)
    
    print_team_report(f"🏠 [홈팀] {home}", q_home, s_home, c_home)
    print("")
    print_team_report(f"✈️  [원정팀] {away}", q_away, s_away, c_away)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    args = parser.parse_args()
    simulate(args.home, args.away)
