import os
import json
import duckdb
from datetime import datetime, timedelta

# Configuration
DATA_DIR = "web/public/data"
DB_PATH = "nba_analytics.duckdb"
ROSTER_FILE = os.path.join(DATA_DIR, "roster_snapshot.json")
DASHBOARD_FILE = os.path.join(DATA_DIR, "dashboard.json")

def check_file_age(filepath, max_hours=24):
    if not os.path.exists(filepath):
        return None, "❌ MISSING"
    
    mtime = os.path.getmtime(filepath)
    dt = datetime.fromtimestamp(mtime)
    age = datetime.now() - dt
    
    status = "✅ FRESH" if age < timedelta(hours=max_hours) else f"⚠️ STALE ({age.days}d {age.seconds//3600}h)"
    return dt.strftime("%Y-%m-%d %H:%M:%S"), status

def verify_data_integrity():
    print("\n" + "="*60)
    print("🔍 SYSTEM DIAGNOSIS REPORT (CONFLICT ENGINE)")
    print("="*60)
    
    # 1. File System Check
    print(f"\n[1] FILE SYSTEM INTEGRITY")
    files_to_check = [ROSTER_FILE, DASHBOARD_FILE, DB_PATH]
    
    for f in files_to_check:
        ts, status = check_file_age(f)
        print(f"   - {os.path.basename(f):<25}: {status:<15} (Last: {ts})")

    # 2. Roster Data Check
    print(f"\n[2] ROSTER DATA AUDIT")
    if os.path.exists(ROSTER_FILE):
        try:
            with open(ROSTER_FILE, 'r') as f:
                roster = json.load(f)
            
            if isinstance(roster, list):
                total_players = len(roster)
                total_teams = len(set(p.get('team_id') for p in roster))
            else:
                total_teams = len(roster.keys())
                total_players = sum(len(team) for team in roster.values())
            
            print(f"   - Total Teams tracked: {total_teams}")
            print(f"   - Total Players tracked: {total_players}")
            
            if total_players < 200:
                print("   ⚠️  WARNING: Player count low (< 200). Run '28_update_rosters.py'.")
            else:
                print("   ✅  Player count healthy.")
                
        except Exception as e:
            print(f"   ❌ JSON Error: {e}")
    else:
        print("   ❌ Roster Snapshot missing. UI will be empty.")

    # 3. DuckDB Integrity
    print(f"\n[3] DATABASE INTEGRITY (DuckDB)")
    if os.path.exists(DB_PATH):
        try:
            con = duckdb.connect(DB_PATH)
            tables = con.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            print(f"   - Tables found: {', '.join(table_names)}")
            
            if 'regime_vectors' in table_names:
                count = con.execute("SELECT COUNT(*) FROM regime_vectors").fetchone()[0]
                print(f"   - Regime Vectors: {count}")
            else:
                print("   ⚠️  'regime_vectors' table MISSING.")
                
            con.close()
            print("   ✅  Database readable.")
        except Exception as e:
            print(f"   ❌ DB Connection Failed: {e}")
    else:
        print("   ❌ Database missing.")

    print("\n" + "="*60)
    print("👉 RECOMMENDATION:")
    
    # Logic for recommendation
    roster_age = check_file_age(ROSTER_FILE)[1]
    
    if "MISSING" in roster_age:
        print("   Run 'python3 28_update_rosters.py' to generate initial data.")
    elif "STALE" in roster_age:
        print("   Data is old. Run 'python3 nba_ops_pipeline.py' to refresh everything.")
    else:
        print("   System looks healthy. Verify Web Dashboard at /live.")
    print("="*60 + "\n")

if __name__ == "__main__":
    verify_data_integrity()
