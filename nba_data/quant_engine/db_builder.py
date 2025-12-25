
import duckdb
import json
import os
import glob
import pandas as pd
from datetime import datetime

# Config
DB_PATH = "/Users/js/g9/nba_analytics.duckdb"
DATA_DIR = "/Users/js/g9/nba_data"

def init_db(con):
    print("Initializng Schema...")
    
    # 1. Teams
    con.execute("DROP TABLE IF EXISTS dim_teams")
    con.execute("""
        CREATE TABLE dim_teams (
            team_id INTEGER PRIMARY KEY,
            team_name VARCHAR,
            team_city VARCHAR,
            team_abbreviation VARCHAR,
            team_slug VARCHAR
        )
    """)
    
    # 2. Players
    con.execute("DROP TABLE IF EXISTS dim_players")
    con.execute("""
        CREATE TABLE dim_players (
            person_id INTEGER PRIMARY KEY,
            display_name VARCHAR,
            team_id INTEGER,
            from_year VARCHAR,
            to_year VARCHAR,
            player_slug VARCHAR
        )
    """)
    
    # 3. Schedule
    con.execute("DROP TABLE IF EXISTS dim_schedule")
    con.execute("""
        CREATE TABLE dim_schedule (
            game_id VARCHAR PRIMARY KEY,
            game_date DATE,
            home_team VARCHAR,
            away_team VARCHAR,
            home_id INTEGER,
            away_id INTEGER,
            arena VARCHAR,
            city VARCHAR
        )
    """)
    
    # 4. Gamelogs (Fact Table)
    con.execute("DROP TABLE IF EXISTS fact_gamelogs")
    con.execute("""
        CREATE TABLE fact_gamelogs (
            game_id VARCHAR,
            person_id INTEGER,
            team_id INTEGER,
            game_date DATE,
            matchup VARCHAR,
            wl VARCHAR,
            min INTEGER,
            fgm INTEGER, fga INTEGER, fg_pct DOUBLE,
            fg3m INTEGER, fg3a INTEGER, fg3_pct DOUBLE,
            ftm INTEGER, fta INTEGER, ft_pct DOUBLE,
            reb INTEGER, ast INTEGER, blk INTEGER, stl INTEGER,
            pf INTEGER, tov INTEGER, pts INTEGER,
            plus_minus INTEGER,
            PRIMARY KEY (game_id, person_id)
        )
    """)
    
    # 5. Upsets (Qualitative)
    con.execute("DROP TABLE IF EXISTS fact_historical_upsets")
    con.execute("""
        CREATE TABLE fact_historical_upsets (
            game_id VARCHAR PRIMARY KEY,
            game_date DATE,
            season INTEGER,
            favorite VARCHAR,
            underdog VARCHAR,
            winner VARCHAR,
            primary_cause VARCHAR,
            secondary_cause VARCHAR,
            reasoning VARCHAR,
            context_json JSON
        )
    """)
    
    print("Schema Created.")

def load_reference(con):
    print("Loading Reference Data (Teams/Players)...")
    roster_path = os.path.join(DATA_DIR, "players/roster_2025.json")
    
    if not os.path.exists(roster_path):
        print(f"Error: {roster_path} missing.")
        return

    with open(roster_path, 'r') as f:
        roster = json.load(f)
        
    # Process Teams (deduplicate)
    teams = {}
    players = []
    
    for p in roster:
        # Team
        t_id = p.get('TEAM_ID')
        if t_id and t_id != 0:
            teams[t_id] = (
                t_id, p.get('TEAM_NAME', ''), p.get('TEAM_CITY', ''), 
                p.get('TEAM_ABBREVIATION', ''), p.get('TEAM_SLUG', '')
            )
        
        # Player
        players.append((
            p['PERSON_ID'], p['DISPLAY_FIRST_LAST'], p['TEAM_ID'],
            p['FROM_YEAR'], p['TO_YEAR'], p['PLAYER_SLUG']
        ))
        
    # Insert Teams
    con.executemany("INSERT OR IGNORE INTO dim_teams VALUES (?, ?, ?, ?, ?)", list(teams.values()))
    print(f"Loaded {len(teams)} Unique Teams.")
    
    # Insert Players
    con.executemany("INSERT OR IGNORE INTO dim_players VALUES (?, ?, ?, ?, ?, ?)", players)
    print(f"Loaded {len(players)} Players.")

def load_schedule(con):
    print("Loading Schedule...")
    sched_path = os.path.join(DATA_DIR, "schedule_2025.json")
    if not os.path.exists(sched_path):
        print("Schedule missing.")
        return
        
    with open(sched_path, 'r') as f:
        sched = json.load(f)
        
    data = []
    for s in sched:
        # Handle Date
        d_str = s['date'].split(' ')[0]
        try:
            # Try MM/DD/YYYY to YYYY-MM-DD
            parts = d_str.split('/')
            if len(parts) == 3:
                iso_date = f"{parts[2]}-{parts[0]}-{parts[1]}"
            else:
                iso_date = d_str
        except:
            iso_date = d_str
            
        data.append((
            s['game_id'], iso_date, s['home_team'], s['away_team'],
            s['home_id'], s['away_id'], s.get('arena',''), s.get('city','')
        ))
    
    con.executemany("INSERT INTO dim_schedule VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)
    print(f"Loaded {len(data)} Games.")

def load_upsets(con):
    print("Loading Upsets...")
    path = os.path.join(DATA_DIR, "quant_engine/upset_library_enriched.json")
    fallback = os.path.join(DATA_DIR, "quant_engine/upset_library_tagged.json")
    
    target = path if os.path.exists(path) else (fallback if os.path.exists(fallback) else None)
    
    if not target:
        print("No upset library found.")
        return

    with open(target, 'r') as f:
        upsets = json.load(f)
        
    data = [] 
    for u in upsets:
        cause = u.get('cause_classification', {})
        ctx = u.get('context', {})
        ctx_json = json.dumps(ctx)
        
        data.append((
            u['game_id'], u['date'], u['season'], u['favorite'], u['underdog'], u['winner'],
            cause.get('primary_cause'), cause.get('secondary_cause'), cause.get('reasoning'),
            ctx_json
        ))
        
    con.executemany("INSERT INTO fact_historical_upsets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
    print(f"Loaded {len(data)} Upsets.")

def load_gamelogs(con):
    print("Loading Gamelogs (ID Mapping: Name-Based)...")
    files = glob.glob(os.path.join(DATA_DIR, "gamelogs_real/*.json"))
    
    # 1. Build Name Map (Normalize)
    print("Building Name Map from DimPlayers...")
    p_rows = con.execute("SELECT display_name, person_id, team_id FROM dim_players").fetchall()
    name_map = {}
    for r in p_rows:
        # Key: lowercase name
        name_map[r[0].lower()] = (r[1], r[2]) # (nba_id, team_id)
        
    print(f"Mapped {len(name_map)} players.")

    # Helper for recursive search
    def extract_stats_recursively(obj, collector):
        if isinstance(obj, dict):
            if 'eventId' in obj and 'stats' in obj:
                collector.append(obj)
                return
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract_stats_recursively(v, collector)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    extract_stats_recursively(item, collector)

    batch_data = []
    
    for fpath in files:
        try:
            basename = os.path.basename(fpath)
            # Format: First_Last_ID.json
            name_part = "_".join(basename.split('_')[:-1]) # Remove last ID
            
            # Construct Name: "Sion_James" -> "Sion James"
            original_name = name_part.replace('_', ' ')
            
            # Lookup
            match = name_map.get(original_name.lower())
            
            if match:
                person_id, team_id = match
            else:
                # If no match, try fuzzy or skip?
                # For this regime, skip unmapped players to avoid noise?
                # Or keep with 0?
                # Better to keep with 0 but try to match.
                # Let's assume ESPN ID for now but TeamId=0 will fail.
                # Actually, if we use ESPN ID, subsequent lookups fail.
                # We need NBA ID.
                continue # Strict matching for now to ensure quality
                
            with open(fpath, 'r') as f:
                data = json.load(f)

            # Metadata in 'events' dict
            if 'events' not in data: continue
            meta_events = data['events']
            
            # Find stats
            processed_stats = []
            extract_stats_recursively(data, processed_stats)
            
            for p_event in processed_stats:
                eid = p_event.get('eventId')
                stats = p_event.get('stats', [])
                
                if not eid or len(stats) < 14: continue 
                
                # Get Metadata
                meta = meta_events.get(eid)
                if not meta: continue
                
                game_date_raw = meta.get('gameDate')
                if not game_date_raw: continue
                game_date = game_date_raw.split('T')[0]

                # Matchup
                if 'opponent' in meta:
                    opp_abbr = meta['opponent']['abbreviation']
                    at_vs = meta.get('atVs', 'vs')
                    matchup = f"{at_vs} {opp_abbr}"
                else:
                    matchup = "Unknown"
                    
                wl = meta.get('gameResult', 'N/A')
                
                # Parse Stats
                try:
                    min_val = int(stats[0])
                    fg = stats[1].split('-')
                    fgm, fga = int(fg[0]), int(fg[1])
                    fg_pct = float(stats[2]) if stats[2] else 0.0
                    
                    fg3 = stats[3].split('-')
                    fg3m, fg3a = int(fg3[0]), int(fg3[1])
                    fg3_pct = float(stats[4]) if stats[4] else 0.0
                    
                    ft = stats[5].split('-')
                    ftm, fta = int(ft[0]), int(ft[1])
                    ft_pct = float(stats[6]) if (len(stats) > 6 and stats[6]) else 0.0
                    
                    reb = int(stats[7])
                    ast = int(stats[8])
                    blk = int(stats[9])
                    stl = int(stats[10])
                    pf = int(stats[11])
                    tov = int(stats[12])
                    pts = int(stats[13])
                    
                    plus_minus = 0
                    if len(stats) > 14 and stats[14]:
                       plus_minus = int(stats[14])

                    batch_data.append((
                        eid, person_id, team_id, # CORRECT IDs
                        game_date, matchup, wl,
                        min_val, fgm, fga, fg_pct,
                        fg3m, fg3a, fg3_pct,
                        ftm, fta, ft_pct,
                        reb, ast, blk, stl,
                        pf, tov, pts,
                        plus_minus 
                    ))
                except:
                    continue
                    
        except Exception as e:
            continue

    # Insert Batch
    if batch_data:
        con.executemany("""
            INSERT INTO fact_gamelogs VALUES (
            ?, ?, ?, ?, ?, ?, 
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?
            )
        """, batch_data)
        
    print(f"Loaded {len(batch_data)} Log Entries (Matched).")

def build():
    con = duckdb.connect(DB_PATH)
    init_db(con)
    load_reference(con)
    load_schedule(con)
    load_upsets(con)
    load_gamelogs(con)
    
    # Validation
    try:
        row = con.execute("SELECT COUNT(*) FROM dim_players").fetchone()
        print(f"\nFinal Check - Players: {row[0]}")
        row = con.execute("SELECT COUNT(*) FROM fact_gamelogs").fetchone()
        print(f"Final Check - Gamelogs: {row[0]}")
    except:
        print("Verification failed.")
        
    con.close()
    print("DB Build Complete.")

if __name__ == "__main__":
    build()
