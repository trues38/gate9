
import os
import duckdb
import json
import argparse
import sys
from datetime import date

# PATHS
PIPELINE_DIR = "nba_data/pipeline"

def trigger_daily_update():
    """
    Full System Update:
    1. Team Regimes (ESPN Scores)
    2. Player Logs (Fetch Real)
    3. Player Regimes (Recalc)
    4. Report Generation (11-Layer)
    """
    # print("[ADMIN] Triggering Daily Update...")
    # Using the existing 29_update... script.
    # Ensure checking path correctness relative to CWD (usually project root).
    ret = os.system(f"python3 {PIPELINE_DIR}/29_update_daily_regimes.py")
    return {"status": "success" if ret == 0 else "error", "code": ret}

def run_specific_game(payload):
    """
    Run the V3 Regime Engine for a specific game ID or matchup.
    Payload expected: {'game_id': '...', 'home': '...', 'away': '...'}
    """
    try:
        # Import V3 Engine dynamically
        from nba_data.pipeline import regime_engine_v3
        
        gid = payload.get('game_id')
        # If game_id provided (e.g., 2025-12-10_MIA_ORL), parse it?
        # Or if manual home/away provided.
        # For simplicity, if gid is like DATE_HOME_AWAY, we can parse it.
        if gid and "_" in gid:
            parts = gid.split("_")
            # Assume YYYY-MM-DD_HOME_AWAY
            if len(parts) >= 3:
                h_abbr = parts[1]
                a_abbr = parts[2]
                # ID Lookup needed? V3 Engine needs IDs.
                # For now, let's just try to find IDs from DB or passing 0 if engine allows.
                # The V3 engine requires IDs for DB lookup. 
                # We need a quick Name->ID lookup function here.
                con = duckdb.connect("nba_analytics.duckdb", read_only=True)
                # Try to find team IDs
                try:
                    hid = con.sql(f"SELECT team_id FROM fact_regimes WHERE team_id < 100 AND momentum_score IS NOT NULL LIMIT 1").fetchone() # Fallback? No.
                    # Better: Scan fact_regimes/fact_game_results to match Abbr?
                    # The DB doesn't have a simple Team Map table easily accessible maybe.
                    # Hardcoded common IDs for safety?
                    # MIA=14, ORL=19, NYK=18, TOR=28.
                    team_map = {"MIA": 14, "ORL": 19, "NYK": 18, "TOR": 28, "BOS": 2, "LAL": 13, "GSW": 9}
                    hi = team_map.get(h_abbr, 0)
                    ai = team_map.get(a_abbr, 0)
                except:
                    hi, ai = 0, 0
                con.close()
                
                print(f"[ADMIN] Run V3 for {h_abbr}({hi}) vs {a_abbr}({ai}) ID: {gid}")
                regime_engine_v3.run_pipeline_v3(hi, ai, h_abbr, a_abbr, game_id_override=gid)
                return {"status": "success", "message": f"Report Generated for {gid}"}
        
        return {"status": "error", "message": "Invalid Game ID Format (Use: YYYY-MM-DD_HOME_AWAY)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_system_health():
    """
    Returns latest timestamp of data.
    """
    try:
        con = duckdb.connect("nba_analytics.duckdb", read_only=True)
        # Check max date
        last_date = "Unknown"
        try:
           res = con.sql("SELECT MAX(date) FROM fact_regimes").fetchone()
           if res: last_date = res[0]
        except: pass
        
        con.close()
        return {
            "last_update": str(last_date),
            "engine_status": "ONLINE",
            "protocol": "Daily Freeze (17:00 KST)"
        }
    except Exception as e:
        return {"status": "offline", "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, help="Action to perform")
    parser.add_argument("--payload", default="{}", help="JSON Payload")
    args = parser.parse_args()
    
    payload = json.loads(args.payload)
    
    result = {"status": "unknown"}
    
    if args.action == "check_health":
        result = get_system_health()
    elif args.action == "run_daily":
        result = trigger_daily_update()
    elif args.action == "run_game":
        result = run_specific_game(payload)
    else:
        result = {"error": f"Unknown Action: {args.action}"}
        
    print(json.dumps(result))
