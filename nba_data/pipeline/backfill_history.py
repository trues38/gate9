
import requests
import json
import duckdb
import os
from datetime import date, datetime, timedelta
import asyncio

# CONFIG
DB_PATH = "nba_analytics.duckdb"

# DATE RANGE (Full Season Backfill)
START_DATE = date(2025, 10, 22) # Season Start
END_DATE = date(2025, 12, 10)

def fetch_espn_scoreboard(target_date):
    """
    Fetch Game Results for a specific date
    """
    date_str = target_date.strftime('%Y%m%d')
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    print(f"   Fetching Scoreboard: {date_str}...")
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def fetch_espn_boxscore(game_id_espn):
    """
    Fetch Boxscore (Lineups/Stats)
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id_espn}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except:
        return None

def process_day(target_date, con):
    print(f"📅 Processing: {target_date}...")
    
    data = fetch_espn_scoreboard(target_date)
    if not data: return

    events = data.get('events', [])
    print(f"   Found {len(events)} games.")
    
    games_upsert = []
    boxscores_upsert = []
    injuries_upsert = [] # Hard to get historical "Out" status from summary alone, usually Inactive list is in boxscore?
    
    for event in events:
        status = event['status']['type']['state']
        if status != 'post': continue
        
        game_id_espn = event['id']
        date_iso = target_date.isoformat()
        
        # 1. Game Results
        comps = event['competitions'][0]
        home = next(c for c in comps['competitors'] if c['homeAway'] == 'home')
        away = next(c for c in comps['competitors'] if c['homeAway'] == 'away')
        
        home_score = int(home['score'])
        away_score = int(away['score'])
        
        # Insert Game Result
        # Table: fact_game_results (game_id, game_date, home_team, away_team, ...)
        # We need Team Abbr
        h_abbr = home['team']['abbreviation']
        a_abbr = away['team']['abbreviation']
        
        # Custom ID for our system: YYYY-MM-DD_HOME_AWAY
        sys_gid = f"{date_iso}_{h_abbr}_{a_abbr}"
        
        # Delete existing
        con.execute(f"DELETE FROM fact_game_results WHERE game_id='{game_id_espn}' OR game_id='{sys_gid}'")
        con.execute(f"DELETE FROM fact_boxscores WHERE game_id='{sys_gid}'")
        
        con.execute(f"""
            INSERT INTO fact_game_results (game_id, game_date, home_team, away_team, home_score, away_score, closing_spread, closing_total, spread_result, total_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sys_gid, target_date, h_abbr, a_abbr, home_score, away_score, 0.0, 0.0, "Pending", "Pending"))
        
        # 2. Boxscore & Lineups
        summary = fetch_espn_boxscore(game_id_espn)
        if not summary: continue
        
        # Process Boxscore
        # Check 'boxscore' -> 'players'
        try:
            bx = summary.get('boxscore', {}).get('players', [])
            for team_bx in bx:
                # TEAM ID MAPPING
                # We need to identify if this 'team_bx' is Home or Away.
                # 'team_bx' has 'team' object with id/abbrev.
                t_info = team_bx.get('team', {})
                t_id_espn = int(t_info.get('id', 0))
                t_abbr = t_info.get('abbreviation')
                
                # We need to map ESPN ID or Abbr to internal duckdb team_id.
                # Hardcoded MAP for 30 teams (Same as in other scripts)
                TEAM_MAP = {
                    "MIA": 14, "MIA ": 14, "ORL": 19, "NYK": 18, "NY": 18, "TOR": 28, "BOS": 2, "PHI": 20, "MIL": 15, "CLE": 5,
                    "LAL": 13, "GSW": 9, "PHX": 21, "SAC": 23, "DEN": 7, "MIN": 16, "OKC": 25, "POR": 22, "UTA": 26, "LAC": 12,
                    "DAL": 6, "HOU": 10, "MEM": 29, "NOP": 17, "NO": 17, "SAS": 24, "SA": 24, "ATL": 1, "CHA": 30, "WAS": 27, "DET": 8, "IND": 11, "CHI": 4, "BKN": 3, "BRK": 3
                }
                # Also support internal integer map if needed, but Abbr is safest from ESPN.
                
                team_id_db = TEAM_MAP.get(t_abbr, 0)
                if team_id_db == 0:
                    # Fallback matches
                    if t_abbr == "GS": team_id_db = 9
                    if t_abbr == "WSH": team_id_db = 27
                    if t_abbr == "UTAH": team_id_db = 26
                
                stats_list = team_bx.get('statistics', [])
                for pl in stats_list[0]['athletes']:
                    p_name = pl['athlete']['displayName']
                    p_id = pl['athlete']['id'] # ESPN ID
                    
                    stats = pl['stats'] # List of strings usually: MIN, FG, 3PT, FT, OREB, DREB, REB, AST, STL, BLK, TO, PF, +/- , PTS
                    # Index mapping varies. Assume Standard ESPN
                    # 0: MIN, 12: PTS? 
                    # Actually standard is [MIN, FG, 3PT, FT, OREB, DREB, REB, AST, STL, BLK, TO, PF, +/-, PTS]
                    # Let's clean MIN
                    # Default to 0
                    s_min=0; s_pts=0; s_reb=0; s_ast=0; s_stl=0; s_blk=0; s_tov=0; s_pf=0; s_pm=0
                    
                    try:
                        # Stats check
                        # Headers: ['MIN', 'PTS', 'FG', '3PT', 'FT', 'REB', 'AST', 'TO', 'STL', 'BLK', 'OREB', 'DREB', 'PF', '+/-']
                        if stats and len(stats) >= 14:
                             s_min = int(stats[0]) if stats[0].isdigit() else 0
                             s_pts = int(stats[1])
                             s_reb = int(stats[5])
                             s_ast = int(stats[6])
                             s_tov = int(stats[7])
                             s_stl = int(stats[8])
                             s_blk = int(stats[9])
                             s_pf = int(stats[12])
                             s_pm = int(stats[13])
                    except:
                        # Parsing error or DNP with text
                        pass
                        
                    con.execute(f"""
                        INSERT INTO fact_boxscores (game_id, game_date, team_id, player_id, name, min, pts, reb, ast, stl, blk, tov, pf, plus_minus)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (sys_gid, target_date, team_id_db, int(p_id), p_name, s_min, s_pts, s_reb, s_ast, s_stl, s_blk, s_tov, s_pf, s_pm))
                    
        except Exception as e:
            print(f"   ⚠️ Boxscore Parse Error: {sys_gid} - {e}")

    con.commit()

def run_backfill():
    if os.path.exists(DB_PATH):
        con = duckdb.connect(DB_PATH)
    else:
        print("❌ DB Not Found")
        return

    curr = START_DATE
    while curr <= END_DATE:
        process_day(curr, con)
        curr += timedelta(days=1)
        
    con.close()
    print("\n✅ Backfill Complete (12/1 - 12/10)")

if __name__ == "__main__":
    run_backfill()
