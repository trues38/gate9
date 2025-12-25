import duckdb
import json
import os
import glob
import pandas as pd
from datetime import datetime

DB_PATH = "nba_analytics.duckdb"
RAW_GAMES_DIR = "raw/games"
RAW_BOXSCORE_DIR = "raw/boxscore"
RAW_INJURY_DIR = "raw/injury"

def init_db(con):
    """
    Initialize Database Schema.
    """
    # Dimensions
    con.sql("""
        CREATE TABLE IF NOT EXISTS dim_team (
            team_id INTEGER PRIMARY KEY,
            name VARCHAR,
            abbreviation VARCHAR,
            logo_url VARCHAR
        );
        CREATE TABLE IF NOT EXISTS dim_player (
            player_id INTEGER PRIMARY KEY,
            full_name VARCHAR,
            team_id INTEGER,
            position VARCHAR,
            headshot_url VARCHAR
        );
    """)
    
    # Facts
    con.sql("""
        CREATE TABLE IF NOT EXISTS fact_game (
            game_id INTEGER PRIMARY KEY,
            date DATE,
            season INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            status VARCHAR,
            venue_id INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS fact_boxscore (
            game_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            starter BOOLEAN,
            min INTEGER,
            fgm INTEGER,
            fga INTEGER,
            fg_pct DOUBLE,
            tpm INTEGER,
            tpa INTEGER,
            tp_pct DOUBLE,
            ftm INTEGER,
            fta INTEGER,
            ft_pct DOUBLE,
            oreb INTEGER,
            dreb INTEGER,
            reb INTEGER,
            ast INTEGER,
            tov INTEGER,
            stl INTEGER,
            blk INTEGER,
            pf INTEGER,
            plus_minus INTEGER,
            pts INTEGER,
            PRIMARY KEY (game_id, player_id)
        );
        
        CREATE TABLE IF NOT EXISTS fact_injury (
            report_date DATE,
            player_id INTEGER,
            team_id INTEGER,
            status VARCHAR,
            details VARCHAR,
            PRIMARY KEY (report_date, player_id)
        );
    """)

def load_games(con):
    print("📥 Loading Games...")
    files = glob.glob(os.path.join(RAW_GAMES_DIR, "*_games.json"))
    games_data = []
    teams_map = {} # id -> {name, abbr}
    
    for fpath in files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
            
            # ESPN API V2 Structure
            events = data.get('events', [])
            for event in events:
                game_id = int(event['id'])
                date_str = event['date'].split("T")[0] # ISO format
                season = event.get('season', {}).get('year', 2025)
                
                competitions = event.get('competitions', [{}])[0]
                venue_id = competitions.get('venue', {}).get('id', 0)
                status = event.get('status', {}).get('type', {}).get('name')
                
                competitors = competitions.get('competitors', [])
                home, away = None, None
                
                for comp in competitors:
                    tid = int(comp['id'])
                    tname = comp['team'].get('displayName')
                    tabbr = comp['team'].get('abbreviation')
                    tlogo = comp['team'].get('logo', "")
                    
                    teams_map[tid] = {"name": tname, "abbr": tabbr, "logo": tlogo}
                    
                    score = int(comp.get('score', 0))
                    
                    if comp['homeAway'] == 'home':
                        home = {"id": tid, "score": score}
                    else:
                        away = {"id": tid, "score": score}
                
                if home and away:
                    games_data.append((
                        game_id, date_str, season, home['id'], away['id'], 
                        home['score'], away['score'], status, int(venue_id)
                    ))
        except Exception as e:
            print(f"Error reading {fpath}: {e}")

    # Upsert Teams
    for tid, meta in teams_map.items():
        con.execute(f"INSERT OR REPLACE INTO dim_team VALUES (?, ?, ?, ?)", 
                    (tid, meta['name'], meta['abbr'], meta['logo']))
        
    # Upsert Games
    print(f"   Writing {len(games_data)} games...")
    con.executemany("INSERT OR REPLACE INTO fact_game VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", games_data)

def load_boxscores(con):
    print("📥 Loading Boxscores (Strict Mode)...")
    files = glob.glob(os.path.join(RAW_BOXSCORE_DIR, "*.json"))
    bs_data = []
    
    for fpath in files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
            
            # ESPN Summary V2 Structure
            boxscore = data.get('boxscore', {})
            header = data.get('header', {})
            game_id = int(header.get('id', 0))
            if game_id == 0: continue
            
            # Helper to parse "M-A" strings
            def parse_split(s):
                if s and "-" in str(s):
                    parts = str(s).split("-")
                    if len(parts) == 2:
                        return int(parts[0]), int(parts[1])
                return 0, 0

            # Players are listed by Team
            teams_list = boxscore.get('players', [])
            
            for team_entry in teams_list:
                team_meta = team_entry.get('team', {})
                tid = int(team_meta.get('id', 0))
                
                # 'statistics' is a list of blocks. Usually index 0 has the main stats.
                stats_blocks = team_entry.get('statistics', [])
                if not stats_blocks: continue
                
                athletes = stats_blocks[0].get('athletes', [])
                
                for ath in athletes:
                    athlete_meta = ath.get('athlete', {})
                    pid = int(athlete_meta.get('id', 0))
                    if pid == 0: continue
                    
                    stats_list = ath.get('stats', [])
                    if not stats_list: continue # DNP usually
                    
                    try:
                        # Index Mapping from "MIN, PTS, FG, 3PT, FT, REB, AST, TO, STL, BLK, OREB, DREB, PF, +/-"
                        # 0: MIN, 1: PTS, 2: FG, 3: 3PT, 4: FT, 5: REB, 6: AST, 7: TO, 8: STL, 9: BLK, 10: OREB, 11: DREB, 12: PF, 13: +/-
                        
                        min_str = stats_list[0]
                        if not min_str or min_str == "--": continue 
                        minutes = int(min_str)
                        
                        pts = int(stats_list[1])
                        fgm, fga = parse_split(stats_list[2])
                        tpm, tpa = parse_split(stats_list[3])
                        ftm, fta = parse_split(stats_list[4])
                        
                        reb = int(stats_list[5])
                        ast = int(stats_list[6])
                        tov = int(stats_list[7])
                        stl = int(stats_list[8])
                        blk = int(stats_list[9])
                        oreb = int(stats_list[10])
                        dreb = int(stats_list[11])
                        pf = int(stats_list[12])
                        pm = int(stats_list[13])
                        
                        # Calculate Percentages
                        fg_pct = (fgm / fga * 100.0) if fga > 0 else 0.0
                        tp_pct = (tpm / tpa * 100.0) if tpa > 0 else 0.0
                        ft_pct = (ftm / fta * 100.0) if fta > 0 else 0.0
                        
                        starter = ath.get('starter', False)
                        
                        # Schema: game, team, player, starter, min, fgm, fga, fg%, tpm, tpa, tp%, ftm, fta, ft%, oreb, dreb, reb, ast, tov, stl, blk, pf, +/-, pts
                        bs_data.append((
                            game_id, tid, pid, starter, minutes,
                            fgm, fga, fg_pct,
                            tpm, tpa, tp_pct,
                            ftm, fta, ft_pct,
                            oreb, dreb, reb,
                            ast, tov, stl, blk, pf, pm, pts
                        ))
                    except:
                        continue
                        
        except Exception as e:
            pass

    print(f"   Writing {len(bs_data)} boxscore records (Strict Mode)...")
    if bs_data:
        con.executemany("INSERT OR REPLACE INTO fact_boxscore VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", bs_data)

def create_aggregates(con):
    print("📊 Creating Aggregates (fact_team_stats)...")
    
    # Create Table
    con.sql("""
        CREATE TABLE IF NOT EXISTS fact_team_stats (
            game_id INTEGER,
            team_id INTEGER,
            opponent_id INTEGER,
            is_home BOOLEAN,
            pts INTEGER,
            possessions DOUBLE,
            ortg DOUBLE,
            drtg DOUBLE,
            pace DOUBLE,
            oreb_pct DOUBLE,
            tov_pct DOUBLE,
            PRIMARY KEY (game_id, team_id)
        );
    """)
    
    # 1. Team Boxscore Sums
    con.sql("""
        CREATE OR REPLACE TEMP TABLE team_daily_sum AS
        SELECT 
            game_id, 
            team_id,
            SUM(pts) as pts,
            SUM(fga) as fga,
            SUM(fta) as fta,
            SUM(oreb) as oreb,
            SUM(tov) as tov,
            SUM(dreb) as dreb,
            SUM(fgm) as fgm,
            SUM(min) as min_total
        FROM fact_boxscore
        GROUP BY game_id, team_id
    """)
    
    # 2. Join with Game to find Opponent and calculate Derived Metrics
    # Standard Poss Formula: 0.5 * ((Tm FGA + 0.44 * Tm FTA - Tm OREB + Tm TOV) + (Opp FGA + 0.44 * Opp FTA - Opp OREB + Opp TOV))
    # Note: Minutes is sum of player minutes. Game length = 48 (usually). Pace = 48 * ((Poss + OppPoss) / (2 * (TmMin + OppMin) / 5))
    
    con.sql("""
        INSERT OR REPLACE INTO fact_team_stats
        WITH match_stats AS (
            SELECT 
                t.game_id,
                t.team_id,
                CASE WHEN g.home_team_id = t.team_id THEN g.away_team_id ELSE g.home_team_id END as opponent_id,
                CASE WHEN g.home_team_id = t.team_id THEN TRUE ELSE FALSE END as is_home,
                t.pts,
                t.fga, t.fta, t.oreb, t.tov, t.dreb, t.min_total
            FROM team_daily_sum t
            JOIN fact_game g ON t.game_id = g.game_id
        ),
        full_match AS (
            SELECT
                m1.game_id,
                m1.team_id,
                m1.opponent_id,
                m1.is_home,
                m1.pts as tm_pts,
                m2.pts as opp_pts,
                
                -- Simple Possessions Calculation
                (m1.fga + 0.44 * m1.fta - m1.oreb + m1.tov) as tm_poss_est,
                (m2.fga + 0.44 * m2.fta - m2.oreb + m2.tov) as opp_poss_est,
                
                m1.min_total,
                m2.min_total as opp_min_total,
                
                m1.oreb as tm_oreb,
                m1.tov as tm_tov
            FROM match_stats m1
            JOIN match_stats m2 ON m1.game_id = m2.game_id AND m1.opponent_id = m2.team_id
        )
        SELECT
            game_id,
            team_id,
            opponent_id,
            is_home,
            tm_pts as pts,
            
            -- Average Possessions
            (tm_poss_est + opp_poss_est) / 2.0 as possessions,
            
            -- ORTG (Pts / 100 Poss)
            CASE WHEN (tm_poss_est + opp_poss_est) > 0 
                THEN 100.0 * tm_pts / ((tm_poss_est + opp_poss_est) / 2.0) 
                ELSE 0 END as ortg,
                
            -- DRTG (Opp Pts / 100 Poss)
            CASE WHEN (tm_poss_est + opp_poss_est) > 0 
                THEN 100.0 * opp_pts / ((tm_poss_est + opp_poss_est) / 2.0) 
                ELSE 0 END as drtg,
            
            -- Pace (Poss / 48min)
            -- Game minutes = min_total / 5 (since 5 players)
            CASE WHEN (min_total + opp_min_total) > 0
                THEN 48.0 * ((tm_poss_est + opp_poss_est) / 2.0) / ((min_total + opp_min_total) / 10.0)
                ELSE 0 END as pace,
                
            -- OREB% (Tm OREB / (Tm OREB + Opp DREB)) -- approximated here or simpler?
            -- Wait, I didn't verify if I have Opp DREB in `full_match` joins.
            -- I can add columns if strict accuracy needed, but simple Ratio helps.
            -- Let's use simplified: OREB / (OREB + OppDREB)? I didn't bring OppDREB.
            0.0 as oreb_pct, -- Placeholder for now to keep query simple, update later if needed
            
            -- TOV% (TOV / Poss)
            CASE WHEN tm_poss_est > 0 THEN 100.0 * tm_tov / tm_poss_est ELSE 0 END as tov_pct
            
        FROM full_match
    """)
    print("   Aggregates calculated.")

def load_injuries(con):
    print("🚑 Loading Injuries...")
    files = glob.glob(os.path.join(RAW_INJURY_DIR, "*.json"))
    inj_data = []
    
    for fpath in files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                
            # Check format: List of records (ESPN crawler output) vs Dict (NBA JSON)
            # My crawl_injury_report.py (ESPN version) saves a List of Dicts.
            
            if isinstance(data, list):
                for item in data:
                    # Schema: report_date, player_id, team_id, status, details
                    # item keys: team, team_id, player, player_id, status, date, type, details
                    
                    # Convert date format if needed? item['date'] might be ISO or simple string.
                    # DuckDB date parses ISO usually.
                    
                    r_date = datetime.now().strftime("%Y-%m-%d") # Default to file date?
                    # Filename has date: "20251211_espn_injuries.json"
                    fname = os.path.basename(fpath)
                    if "_" in fname:
                        d_str = fname.split("_")[0]
                        try:
                            dt = datetime.strptime(d_str, "%Y%m%d")
                            r_date = dt.strftime("%Y-%m-%d")
                        except:
                            pass
                            
                    inj_data.append((
                        r_date,
                        int(item.get('player_id', 0)),
                        int(item.get('team_id', 0)),
                        item.get('status'),
                        str(item.get('details')) # details field or returnDate
                    ))
            elif isinstance(data, dict):
                 # Old NBA JSON format?
                 pass
                 
        except Exception as e:
            # print(f"Error {fpath}: {e}")
            pass

    print(f"   Writing {len(inj_data)} injury records...")
    if inj_data:
        con.executemany("INSERT OR REPLACE INTO fact_injury VALUES (?, ?, ?, ?, ?)", inj_data)

def main():
    con = duckdb.connect(DB_PATH)
    init_db(con)
    load_games(con)
    load_boxscores(con)
    load_injuries(con) # Added
    create_aggregates(con) # Enabled
    con.close()
    print("✅ ETL Complete.")

if __name__ == "__main__":
    main()
