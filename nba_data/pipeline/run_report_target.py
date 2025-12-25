import os
import json
import duckdb
import sys
import argparse
from datetime import datetime

# Path setup
DATA_DIR = "/Users/js/g9/nba_data"
sys.path.append(DATA_DIR)

# Import Fetcher
from pipeline.fetch_daily_target import fetch_data_for_date
# Import Tag Engine (Report V3)
from quant_engine_v1 import tag_engine

def get_team_map():
    con = duckdb.connect("/Users/js/g9/nba_analytics.duckdb", read_only=True)
    res = con.execute("SELECT team_id, team_name, team_city, team_slug FROM dim_teams").fetchall()
    con.close()
    
    # Map "City Name" -> ID, "Name" -> ID, "City" -> ID
    tmap = {}
    for r in res:
        tid, name, city, slug = r
        tmap[name] = tid
        tmap[city] = tid
        tmap[f"{city} {name}"] = tid
        tmap[slug] = tid
        
    # Manual overrides for common ESPN discrepancies
    tmap["LA Clippers"] = tmap.get("Clippers")
    tmap["Los Angeles Clippers"] = tmap.get("Clippers")
    tmap["Los Angeles Lakers"] = tmap.get("Lakers")
    return tmap

def parse_matchup(matchup_str, tmap):
    # "New York Knicks at Orlando Magic"
    if " at " in matchup_str:
        parts = matchup_str.split(" at ")
    elif " vs " in matchup_str:
        parts = matchup_str.split(" vs ") # Usually 'Home vs Away' in some headers, or 'Away vs Home'?
        # ESPN API usually uses 'Name at Name' for summary.
    else:
        return None, None
        
    if len(parts) != 2: return None, None
    
    # ESPN order: Away at Home
    away_name = parts[0].strip()
    home_name = parts[1].strip()
    
    hid = tmap.get(home_name)
    aid = tmap.get(away_name)
    
    return hid, aid

def run_pipeline(target_date):
    # 1. Fetch Data
    # Format target_date YYYY-MM-DD -> YYYYMMDD
    compact_date = target_date.replace("-", "")
    fetch_data_for_date(compact_date)
    
    # 2. Load Data and Build Matches
    tmap = get_team_map()
    stories_dir = os.path.join(DATA_DIR, "stories_raw")
    
    matches = []
    
    for fname in os.listdir(stories_dir):
        if not fname.endswith(".json"): continue
        path = os.path.join(stories_dir, fname)
        with open(path, 'r') as f:
            data = json.load(f)
            
        if data.get('date') != compact_date:
            continue
            
        # Parse Matchup
        matchup = data.get('matchup', '')
        hid, aid = parse_matchup(matchup, tmap)
        
        if not hid or not aid:
            print(f"Skipping {matchup}: Could not resolve IDs")
            continue
            
        # Extract Odds
        odds = data.get('odds', {})
        line = 0.0
        ou = 220.0
        
        if odds and odds.get('valid'):
            # Parse Details "NY -4.5"
            details = odds.get('details', '')
            import re
            m = re.search(r'([-+]?\d+\.?\d*)', details.split()[-1])
            if m:
                line = float(m.group(1))
            
            # Parse OU
            ou_val = odds.get('overUnder')
            if ou_val:
                try: ou = float(ou_val)
                except: pass
                
        matches.append({
            "game_id": data.get('game_id'), # ESPN ID
            "home_id": hid,
            "away_id": aid,
            "home_team": tmap.get(hid, "Unknown"), # We need Name?
            # Fusion generator load_team_map might want IDs or Names?
            # It usually resolves ID->Name itself.
            "date": target_date,
            "home_line": line,
            "over_under": ou,
            "is_active": True
        })
        
    print(f"Prepared {len(matches)} matches for Report.")
    
    # 3. Generate Report
    # Access internal quant engine
    # We must invoke the generator.
    # We can import it.
    
    p = os.path.join(DATA_DIR, "quant_engine_v1")
    sys.path.append(p)
    p = os.path.join(DATA_DIR, "quant_engine_v1")
    sys.path.append(p)
    from rdata_engine import RDataEngine
    
    # Initialize Engine
    print("🚀 Initializing Lean RData Engine (V2)...")
    engine = RDataEngine()
    
    # Enrich Matches
    for m in matches:
        try:
             odds_val = {
                 'spread': m.get('home_line'),
                 'over_under': m.get('over_under')
             }
             
             # Format Date
             iso_date = target_date
             if len(target_date) == 8 and "-" not in target_date:
                 iso_date = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
             
             res = engine.analyze_matchup(m['home_id'], m['away_id'], iso_date, odds=odds_val, game_id=m['game_id'])
             
             ma = res['market_analysis']
             
             # Update Match Record
             m.update({
                "edge_score": res['edge_score'],
                "risk_score": res['risk_score'],
                "twin_alert": res['twin_alert'],
                "market_data": ma,
                "decomposition": ma.get('decomposition'),
                "game_type": res['game_type'],
                "triggers": ma.get('triggers', []),
                "prob_dist": ma.get('prob_dist', {}),
                "reality_check": ma.get('reality_check', {}),
                "expected_margin": ma.get('expected_margin'),
                "market_line": ma.get('market_line'),
                "delta": ma.get('delta'),
                "signal": ma.get('signal'),
                
                "home_volatility": res['home_stats']['volatility'],
                "away_volatility": res['away_stats']['volatility'],
                "home_pace": res['home_stats']['pace'],
                "away_pace": res['away_stats']['pace']
             })
             
             # --- Report V4: Profile Engine ---
             # We use the raw row (with injected odds) to determine profiles.
             from quant_engine_v1 import profile_engine
             raw_row = res.get('raw_row', {})
             profile_data = profile_engine.build_game_profile(raw_row)
             # Expected output: {'profiles': {FLOW:..., FATIGUE:...}}
             print(f"DEBUG: {m['home_id']} Profiles Generated: {list(profile_data['profiles'].keys())}")
             
             m['profiles'] = profile_data['profiles']
             # m['narrative_summary'] = LEGACY REMOVED
             # m['narrative_tags'] = LEGACY REMOVED
             
             # --- Multi-Modal Twin Engine (Phase 2) ---
             # Triggered by twin_alert == 'Active'
             m['twin_data'] = None
             if m.get('twin_alert') == 'Active':
                 try:
                     print(f"DEBUG: Running Twin Engine for {m['game_id']}...")
                     # Lazy Import to avoid path issues if not needed
                     import find_twin_upset_v2
                     twin_engine = find_twin_upset_v2.TwinEngineV2()
                     
                     context = {
                        "location": "HOME",
                        "streak": 0,
                        "rest_days": m.get('home_rest', 1)
                     }
                     vector = []
                     twins = twin_engine.find_twins(context, vector)
                     if twins:
                        best_twin = twins[0]
                        m['twin_data'] = best_twin
                        m['twin_data']['twin_story'] = {
                            "headline": f"Similar to {best_twin['matchup']}",
                            "reasoning": f"Matched via {best_twin['cause']}",
                            "date": best_twin['date'],
                            "matchup": best_twin['matchup']
                        }
                 except Exception as te:
                     print(f"⚠️ Twin Engine Failed: {te}")
                     m['twin_data'] = None
             else:
                 pass # Skipped based on Alert Logic (Low Risk)
             
        except Exception as e:
            print(f"❌ Engine Error for {m['game_id']}: {e}")
            
    # Generate Report
    try:
        import fusion_report_generator
        print(f"DEBUG: Generator Path: {fusion_report_generator.__file__}")
        from fusion_report_generator import generate_markdown_report
        generate_markdown_report(target_date, matches)
    except ImportError as e:
        print(f"Error importing generator: {e}")
        # Try finding where it is
        print("PYTHONPATH:", sys.path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    run_pipeline(args.date)
