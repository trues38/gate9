
import os
import json
import datetime
import subprocess
from supabase import create_client, Client

# CONFIG (Secrets from GitHub Actions)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def run_ops_pipeline():
    print("🚀 STARTING SAAS OPS PIPELINE (Subprocess Mode)...")
    
    # 0. Initialize Status
    status = {
        "timestamp": str(datetime.datetime.now()),
        "steps": [],
        "errors": [],
        "success": False
    }
    
    # 1. Supabase Connection (Override Sync)
    # ... (Keep existing Sync Logic) ...
    # (I will keep the Sync logic unchanged in the real file, just showing head here)
    
    # [Sync Logic Block - Assumed untouched unless I include it in replacement]
    # Wait, replace_file_content replaces a block. I need to be careful not to delete the Sync logic.
    # The Sync logic is lines 25-50.
    # I should target the IMPORTS (Lines 1-8) and the CALL SITES (Lines 60+).
    # Since they are far apart, I'll use multi_replace or just execute it cleanly.
    # I'll replace the TOP IMPORTS first.
    pass

if __name__ == "__main__":
    pass
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def run_ops_pipeline():
    print("🚀 STARTING SAAS OPS PIPELINE...")
    
    # 0. Initialize Status
    status = {
        "timestamp": str(datetime.datetime.now()),
        "steps": [],
        "errors": [],
        "success": False
    }
    
    # 1. Supabase Connection (Override Sync)
    overrides = []
    try:
        if SUPABASE_URL and SUPABASE_KEY:
            sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Fetch recent overrides
            res = sb.table("ops_overrides").select("*").gte("target_date", str(datetime.date.today())).execute()
            overrides = res.data
            print(f"✅ Fetched {len(overrides)} Overrides from Supabase.")
            status['steps'].append(f"Fetched {len(overrides)} Overrides")
            
            # --- CRITICAL: INJECT OVERRIDES INTO LOCAL DUCKDB ---
            import duckdb
            con = duckdb.connect("nba_analytics.duckdb")
            # Ensure table exists (idempotent)
            con.execute("CREATE TABLE IF NOT EXISTS ops_overrides (target_date DATE, entity_type TEXT, entity_id TEXT, field TEXT, new_value TEXT, notes TEXT)")
            
            for o in overrides:
                # Sync logic: Delete existing for same entity first? No, just insert latest.
                # Simplest for now: Insert
                con.execute("INSERT INTO ops_overrides (target_date, entity_type, entity_id, field, new_value, notes) VALUES (?, ?, ?, ?, ?, ?)",
                           (o['target_date'], o['entity_type'], o['entity_id'], o['field'], o['new_value'], o.get('notes', '')))
            con.close()
            print("✅ Synced Overrides to Local DuckDB.")
            
        else:
             print("⚠️ SUPABASE_URL/KEY missing. Skipping Override Sync.")
             status['errors'].append("Supabase Config Missing")
             
    except Exception as e:
        print(f"❌ Override Sync Failed: {e}")
        status['errors'].append(str(e))

    # 2. Daily Regime Update
    try:
        subprocess.run(["python3", "nba_data/pipeline/29_update_daily_regimes.py"], check=True)
        status['steps'].append("Daily Regimes Updated")
    except Exception as e:
        print(f"❌ Regime Update Failed: {e}")
        status['errors'].append(f"Regime Update: {str(e)}")

    # 3. Report Generation (Batch)
    try:
        # Assuming current date
        # Note: batch_runner usually takes args, let's assume it defaults to today or we modify it
        # Modifying batch_runner to be callable without args or passing arg here
        # For now, calling via subprocess or direct import if refactored
        # The imported 'batch_process_games' doesn't exist yet, we only have the script.
        # Let's run it as a subprocess to be safe/consistent with existing logic
        import subprocess
        subprocess.run(["python3", "nba_data/pipeline/26_batch_runner.py"], check=True)
        status['steps'].append("Batch Reports Generated")
    except Exception as e:
        print(f"❌ Batch Gen Failed: {e}")
        status['errors'].append(f"Batch Gen: {str(e)}")
        
    # 4. Generate Roster Snapshot for Frontend
    try:
        con = duckdb.connect("nba_analytics.duckdb", read_only=True)
        rows = con.execute("SELECT team_id, player_name, is_starter, last_pts, status FROM fact_rosters WHERE date = (SELECT MAX(date) FROM fact_rosters)").fetchall()
        con.close()
        
        roster_map = {}
        for r in rows:
            tid = r[0]
            if tid not in roster_map: roster_map[tid] = []
            roster_map[tid].append({
                "name": r[1],
                "starter": r[2],
                "last_pts": r[3],
                "status": r[4]
            })
            
        os.makedirs("web/public/data", exist_ok=True)
        with open("web/public/data/roster_snapshot.json", "w") as f:
            json.dump(roster_map, f)
        
        status['steps'].append("Roster Snapshot Created")
        print("✅ Roster Snapshot Saved.")
    except Exception as e:
        print(f"⚠️ Roster Snapshot Failed: {e}")

    # 5. Final Status Write (To Supabase)
    status['success'] = len(status['errors']) == 0
    
    try:
        if SUPABASE_URL and SUPABASE_KEY:
            sb.table("admin_system_status").insert({
               "last_run_status": "SUCCESS" if status['success'] else "FAILURE",
               "last_run_log": json.dumps(status),
               "processed_count": 0 # Placeholder
            }).execute()
            print("✅ Status written to Supabase.")
    except Exception as e:
        print(f"⚠️ Failed to write status to Supabase: {e}")
        
    # 5. Write Local JSON for Git Commit
    with open("admin_status.json", "w") as f:
        json.dump(status, f, indent=2)
        
    if not status['success']:
        exit(1) # Fail the GitHub Action

if __name__ == "__main__":
    run_ops_pipeline()
