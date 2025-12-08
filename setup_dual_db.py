import duckdb
import sqlite3
import os
import glob
from pathlib import Path

# Paths
BASE_DIR = Path("nba_data")
GAMELOGS_PATTERN = str(BASE_DIR / "gamelogs/**/*.csv")
REGIMES_JSON = str(BASE_DIR / "regimes/current_regimes.json")

DUCK_DB_PATH = "nba_analytics.db"
SQLITE_DB_PATH = "nba_state.db"

def setup_duckdb():
    print(f"🦆 Initializing DuckDB: {DUCK_DB_PATH}...")
    try:
        con = duckdb.connect(DUCK_DB_PATH)
        
        # 1. Ingest GameLogs (CSV) - Massive Bulk Load
        # We use read_csv_auto to infer types.
        print(f"   PLEASE WAIT: Scanning {GAMELOGS_PATTERN}...")
        # Check if files exist first
        files = glob.glob(GAMELOGS_PATTERN, recursive=True)
        if not files:
            print("   ⚠️ No CSV files found in gamelogs/ directory.")
        else:
            print(f"   Found {len(files)} CSV files. Loading...")
            # Create table directly from glob pattern
            # Using UNION_BY_NAME to handle slight schema variations across seasons
            con.execute(f"""
                CREATE OR REPLACE TABLE gamelogs AS 
                SELECT * FROM read_csv_auto('{GAMELOGS_PATTERN}', union_by_name=true, filename=true)
            """)
            count = con.execute("SELECT COUNT(*) FROM gamelogs").fetchone()[0]
            print(f"   ✅ Loaded {count} rows into 'gamelogs'.")

        # 2. Ingest Regimes (JSON)
        # DuckDB handles JSON list of objects automatically
        if os.path.exists(REGIMES_JSON):
            print(f"   Loading Regimes from {REGIMES_JSON}...")
            con.execute(f"""
                CREATE OR REPLACE TABLE regimes AS 
                SELECT * FROM read_json_auto('{REGIMES_JSON}')
            """)
            count = con.execute("SELECT COUNT(*) FROM regimes").fetchone()[0]
            print(f"   ✅ Loaded {count} rows into 'regimes'.")
        else:
            print(f"   ⚠️ File not found: {REGIMES_JSON}")
            
        con.close()
        print("🦆 DuckDB Setup Complete.\n")
        
    except Exception as e:
        print(f"❌ DuckDB Error: {e}")

def setup_sqlite():
    print(f"💾 Initializing SQLite: {SQLITE_DB_PATH}...")
    try:
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        
        # 1. Schedule / Apps State Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_schedule (
                game_id TEXT PRIMARY KEY,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                status TEXT,
                result TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Reports Cache (Generated Content)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                model_used TEXT,
                content_html TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id)
            )
        """)
        
        # 3. User Logs / Metadata
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.commit()
        con.close()
        print("💾 SQLite Setup Complete.")
        
    except Exception as e:
        print(f"❌ SQLite Error: {e}")

if __name__ == "__main__":
    current_dir = os.getcwd()
    print(f"📂 Working Directory: {current_dir}")
    
    # 0. Clean old DBs if user wants fresh start (optional, safer to keep for now or overwrite)
    # DuckDB 'CREATE OR REPLACE' handles overwrite. SQLite 'IF NOT EXISTS' handles safety.
    
    setup_duckdb()
    setup_sqlite()
    print("\n✅ ULTRA-SPEED LOCAL DB SYSTEM READY.")
