import os
import json
import duckdb
import sys
import argparse
from datetime import datetime

# Path setup
DATA_DIR = "/Users/js/g9/nba_data"
sys.path.append(DATA_DIR)

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
    
    # Manual overrides
    tmap["LA Clippers"] = tmap.get("Clippers")
    tmap["Los Angeles Clippers"] = tmap.get("Clippers")
    tmap["Los Angeles Lakers"] = tmap.get("Lakers")
    return tmap

def parse_matchup(matchup_str, tmap):
    # "New York Knicks at Orlando Magic"
    if " at " in matchup_str:
        parts = matchup_str.split(" at ")
    elif " vs " in matchup_str:
        parts = matchup_str.split(" vs ")
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
    print(f"--- Running MANUAL Report for {target_date} ---")
    
    # NO FETCH STEP
    
    # 2. Load Data and Build Matches
    tmap = get_team_map()
    stories_dir = os.path.join(DATA_DIR, "stories_raw")
    
    matches = []
    
    # Check if folder empty
    files = [f for f in os.listdir(stories_dir) if f.endswith(".json")]
    if not files:
        print("No story files found!")
        return

    # Format Date for Match Logic
    compact_date = target_date.replace("-", "")

    for fname in files:
        path = os.path.join(stories_dir, fname)
        with open(path, 'r') as f:
            data = json.load(f)
            
        # Optional: Check date? Manual files have "20251214".
        if data.get('date') != compact_date:
            print(f"Skipping {fname} (Date mismatch: {data.get('date')})")
            continue
            
        # Parse Matchup
        matchup = data.get('matchup', '')
        hid, aid = parse_matchup(matchup, tmap)
        
        if not hid or not aid:
            print(f"Skipping {matchup}: Could not resolve IDs (Check Names!)")
            # Debug names
            if " at " in matchup:
                p = matchup.split(" at ")
                print(f"  Parsed: '{p[0]}' / '{p[1]}'")
                print(f"  IDs: {tmap.get(p[0])} / {tmap.get(p[1])}")
            continue
            
        # Extract Odds
        odds = data.get('odds', {})
        line = 0.0
        ou = 220.0
        
        if odds and odds.get('valid'):
            # Parse Spread
            # "NY -4.5" -> -4.5
            # "OKC -9.5" -> -9.5
            # My logic in run_report_target uses regex on 'details'
            details = odds.get('details', '')
            import re
            # Find number at end? "NY -4.5"
            m = re.search(r'([-+]?\d+\.?\d*)', details.split()[-1])
            if m:
                line = float(m.group(1))
            
            # Parse OU
            ou_val = odds.get('overUnder')
            if ou_val:
                try: ou = float(ou_val)
                except: pass
        
        # Override for "Manual" if regex fails
        if line == 0.0 and odds.get('spread'):
            try: line = float(odds.get('spread'))
            except: pass
                
        # --- MANUAL ENRICHMENT (Mocking Engine) ---
        # Because Cache is missing future data or specific IDs, we simulate the output.
        
        # 1. Upset Regime Logic
        tier = "0"
        regime_label = "None"
        abs_line = abs(line)
        twin_alert = "None"
        
        if abs_line >= 9.5:
             tier = "3"
             regime_label = "Danger"
             twin_alert = "Regime 3 (Danger) - High Upset Risk"
        elif abs_line >= 6.5:
             tier = "2"
             regime_label = "Caution"
             twin_alert = "Regime 2 (Caution)"
        elif abs_line >= 4.5:
             tier = "1"
             regime_label = "Trap"
             twin_alert = "Regime 1 (Trap) - Common Upset"
             
        # 2. Stats (Mocked for Demo)
        # Knicks vs Magic
        if "Knicks" in data.get('matchup', ''):
            h_mom = 65.0 # Magic doing well?
            a_mom = 72.0 # Knicks 17-7
            h_vol = 10.5
            a_vol = 14.2 # Knicks high vol?
            edge = 45 # Away Edge
        # Spurs vs Thunder
        elif "Spurs" in data.get('matchup', ''):
            h_mom = 85.0 # Thunder 24-1
            a_mom = 60.0 # Spurs 17-7
            h_vol = 9.8  # Thunder Stable
            a_vol = 18.5 # Wemby Volatility
            edge = 75 # Home Edge
            
            # Tier 3 Specific Logic
            if tier == "3":
                twin_alert = f"Regime 3 (Danger): High Volatility Underdog ({a_vol})"
        else:
            h_mom, a_mom = 50.0, 50.0
            h_vol, a_vol = 10.0, 10.0
            edge = 50
            
        matches.append({
            "game_id": data.get('game_id'),
            "home_id": hid,
            "away_id": aid,
            "home_team": tmap.get(hid, "Unknown"),
            "away_team": tmap.get(aid, "Unknown"),
            "date": target_date,
            "home_line": line,
            "over_under": ou,
            "is_active": True,
            
            # Enriched Keys
            "edge_score": edge,
            "risk_score": int(h_vol + a_vol),
            "twin_alert": twin_alert,
            "home_momentum": h_mom,
            "away_momentum": a_mom,
            "home_volatility": h_vol,
            "away_volatility": a_vol,
            "home_pace": 98.5,
            "away_pace": 99.2,
            "game_type": regime_label,
            "market_data": {
                "headline": data.get('headline'),
                "delta": 0.0,
                "signal": "RATIONAL",
                "market_line": line,
                "expected_margin": line - 1.0 if edge > 50 else line + 1.0,
                "is_active": True
            }
        })
        
    print(f"Prepared {len(matches)} matches for Report.")
    
    # 3. Generate Report
    sys.path.append(os.path.join(DATA_DIR, "quant_engine"))
    try:
        from fusion_report_generator import generate_markdown_report
        generate_markdown_report(target_date, matches)
    except ImportError as e:
        print(f"Error importing generator: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    run_pipeline(args.date)
