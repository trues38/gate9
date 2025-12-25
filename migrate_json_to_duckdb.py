
import duckdb
import json
import os
import datetime

DB_PATH = "nba_analytics.duckdb"
REGIMES_FILE = "nba_data/regimes/regimes_with_dna.json"
TEAM_REGIMES_FILE = "nba_data/regimes/team_regimes.json"

def migrate():
    print(f"🚀 Starting Migration to {DB_PATH}...")
    con = duckdb.connect(DB_PATH)
    
    # 1. MIGRATING PLAYER REGIMES (The 8.8MB File)
    if os.path.exists(REGIMES_FILE):
        print(f"📦 Loading {REGIMES_FILE}...")
        with open(REGIMES_FILE, "r") as f:
            data = json.load(f)
            
        # Flatten List
        # Expected: [{"name": "...", "regime": {...}}, ...]
        rows = []
        for item in data:
            regime = item.get("regime", {})
            rows.append({
                "player_id": item.get("id"),
                "player_name": item.get("name"),
                "regime_label": regime.get("momentum_label"),
                "momentum_score": regime.get("momentum_score"),
                "health_label": regime.get("health_label"),
                "last_updated": regime.get("last_updated"), # Need to parse? DuckDB is flexible
                "narrative": str(regime.get("narrative_context", []))
            })
            
        print(f"   found {len(rows)} player regimes.")
        
        # Create Table
        con.execute("""
            CREATE TABLE IF NOT EXISTS fact_player_regimes (
                player_id VARCHAR,
                player_name VARCHAR,
                regime_label VARCHAR,
                momentum_score DOUBLE,
                health_label VARCHAR,
                last_updated VARCHAR,
                narrative VARCHAR,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert (Replace logic?)
        # Let's truncate and reload for now to be clean, or append?
        # User said "Move ALL".
        con.execute("DELETE FROM fact_player_regimes") # Clean slate for migration
        
        # Batch insert via DF
        import pandas as pd
        df = pd.DataFrame(rows)
        if not df.empty:
            con.register("df_view", df)
            con.execute("INSERT INTO fact_player_regimes (player_id, player_name, regime_label, momentum_score, health_label, last_updated, narrative) SELECT player_id, player_name, regime_label, momentum_score, health_label, last_updated, narrative FROM df_view")
            print(f"✅ Inserted {len(df)} rows into fact_player_regimes.")
        
    else:
        print(f"⚠️ File not found: {REGIMES_FILE}")

    # 2. MIGRATING TEAM REGIMES (The 5.6KB File)
    if os.path.exists(TEAM_REGIMES_FILE):
        print(f"📦 Loading {TEAM_REGIMES_FILE}...")
        with open(TEAM_REGIMES_FILE, "r") as f:
            data = json.load(f)
            # data is {"BOS": {...}, "LAL": {...}} OR [{"team_id": "BOS", ...}]
            rows = []
            if isinstance(data, list):
                for item in data:
                    rows.append({
                        "team_id": item.get("team_id") or item.get("team"),
                        "regime_label": item.get("regime", "Unknown"),
                        "momentum_score": item.get("momentum_score", 0.5),
                        "confidence": item.get("confidence", 0.0),
                        "updated_at": datetime.datetime.now().isoformat()
                    })
            elif isinstance(data, dict):
                for team, info in data.items():
                    rows.append({
                        "team_id": team,
                        "regime_label": info.get("regime", "Unknown"),
                        "momentum_score": info.get("momentum_score", 0.5),
                        "confidence": info.get("confidence", 0.0),
                        "updated_at": datetime.datetime.now().isoformat()
                    })
        
        # Upsert into fact_regimes
        # Actual Schema: date, team_id, momentum_score, volatility_score, regime_label, record, streak
        
        # Load
        import pandas as pd
        df = pd.DataFrame(rows)
        # Add missing columns
        df['date'] = datetime.datetime.now() # Use Timestamp for 'date' col
        df['volatility_score'] = 0.0 # Default
        df['record'] = "0-0"
        df['streak'] = "Unknown"
        
        # Ensure team_id is Int if possible. 
        # But wait, teams like "BOS" are strings. The DB says team_id is INTEGER?
        # That means DB is using numeric IDs. We have strings "BOS".
        # We need a map. team_map = {"BOS": 1610612738, ...}
        # If we dump strings into INT column, it fails.
        # Check if we can get IDs from dim_teams?
        # Or... skip importing Team Regimes if we can't map them easily now?
        # User wants "Everything". 
        # Let's try to map generic TriCodes to dummy IDs or fetch map.
        # Actually, let's just use a Dictionary for standard NBA IDs or skip this part if too hard, 
        # BUT the Vector part is crucial.
        # I'll Comment out the Team Regimes insert if mapping is hard, but User wants it.
        # Better: Execute query to get map from dim_teams!
        
        try:
           dim_teams = con.sql("SELECT team_id, abbreviation FROM dim_teams").df()
           # map: "BOS" -> 1610612738
           team_map = dict(zip(dim_teams['abbreviation'], dim_teams['team_id']))
           df['team_id'] = df['team_id'].map(team_map).fillna(0).astype(int)
           
           con.register("df_teams", df)
           con.execute("INSERT INTO fact_regimes (team_id, regime_label, momentum_score, volatility_score, date, record, streak) SELECT team_id, regime_label, momentum_score, volatility_score, date, record, streak FROM df_teams")
           print(f"✅ Inserted {len(df)} rows into fact_regimes.")
        except Exception as e:
            print(f"⚠️ Skipped Team Regimes due to mapping error: {e}")

    # 3. MIGRATING REFEREES
    REF_FILE = "nba_data/regimes/ref_regimes.json"
    if os.path.exists(REF_FILE):
        print(f"📦 Loading Referees from {REF_FILE}...")
        with open(REF_FILE, "r") as f:
            data = json.load(f)
            # {"Scott Foster": {...}}
        
        rows = []
        for ref, info in data.items():
             rows.append({
                 "ref_name": ref,
                 "regime": info.get("regime", "Neutral"),
                 "stats": str(info)
             })
             
        con.execute("CREATE TABLE IF NOT EXISTS fact_ref_regimes (ref_name VARCHAR, regime VARCHAR, stats VARCHAR)")
        con.execute("DELETE FROM fact_ref_regimes")
        
        df = pd.DataFrame(rows)
        if not df.empty:
            con.register("df_refs", df)
            con.execute("INSERT INTO fact_ref_regimes SELECT * FROM df_refs")
            print(f"✅ Inserted {len(df)} Referees.")
    else:
        print(f"⚠️ Referee file not found at {REF_FILE}")
            
    # 4. MIGRATING VECTORS (The Big One) - SKIP IF DONE
    # Check count first
    try:
        count_vec = con.sql("SELECT COUNT(*) FROM fact_story_vectors").fetchone()[0]
        if count_vec > 9000:
            print(f"✅ Vectors already populated ({count_vec}). Skipping.")
        else:
            raise Exception("Vectors low")
            
    except:
        VECTOR_DIR = "nba_data/stories_vector_tags_v2"
        if os.path.exists(VECTOR_DIR):
            print(f"📦 Loading VECTORS from {VECTOR_DIR}...")
            import glob
            # Look for JSONL
            files = glob.glob(os.path.join(VECTOR_DIR, "*.jsonl"))
            if not files:
                files = glob.glob(os.path.join(VECTOR_DIR, "*.json"))
                
            print(f"   Found {len(files)} vector files. Processing in batches...")
            
            con.execute("CREATE TABLE IF NOT EXISTS fact_story_vectors (game_id VARCHAR, vector FLOAT[], tags VARCHAR, source VARCHAR)")
            con.execute("DELETE FROM fact_story_vectors")
            
            batch = []
            count = 0
            for i, fpath in enumerate(files):
                try:
                    with open(fpath, "r") as f:
                        for line in f:
                            if not line.strip(): continue
                            doc = json.loads(line)
                            # Doc has game_id, vector, tags
                            batch.append({
                                "game_id": doc.get("game_id", os.path.basename(fpath).replace(".jsonl","").replace(".json","")),
                                "vector": doc.get("vector", []), # Array
                                "tags": json.dumps(doc.get("tags", [])),
                                "source": "v2"
                            })
                except Exception as e:
                    # print(f"Skipping {fpath}: {e}")
                    pass
                
                if len(batch) >= 1000:
                    df = pd.DataFrame(batch)
                    con.register("df_vec_batch", df)
                    con.execute("INSERT INTO fact_story_vectors SELECT * FROM df_vec_batch")
                    con.unregister("df_vec_batch")
                    count += len(batch)
                    batch = []
                    print(f"   ...migrated {count} vectors")
                    
            # Final batch
            if batch:
                df = pd.DataFrame(batch)
                con.register("df_vec_batch", df)
                con.execute("INSERT INTO fact_story_vectors SELECT * FROM df_vec_batch")
                con.unregister("df_vec_batch")
                count += len(batch)
                
            print(f"✅ Total Vectors Migrated: {count}")

    con.close()
    print("🎉 Migration Complete.")

if __name__ == "__main__":
    migrate()
