import os
import sys
import json
import argparse
import asyncio
import duckdb
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Add path for internal modules
sys.path.append(os.path.join(os.getcwd(),'nba_data/pipeline'))

# Import specific modules (Lazy import to avoid circular dep if needed)
# from nba_data.pipeline import 30_terminal_view as terminal_view
# from nba_data.pipeline import 31_report_agent as report_agent

load_dotenv()

# Setup Paths
REPORT_DIR = "web/public/reports"
TERMINAL_VIEW_DIR = "web/public/terminal_view" # Saving here for frontend access too
DB_PATH = "reports.db"

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(TERMINAL_VIEW_DIR, exist_ok=True)

# Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

def init_sqlite():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        generated_at TIMESTAMP,
        game_id TEXT,
        status TEXT,
        file_path TEXT
    )''')
    conn.commit()
    conn.close()

def log_status(game_id, status, file_path=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Upsert logic
    c.execute("INSERT OR REPLACE INTO reports (id, generated_at, game_id, status, file_path) VALUES (?, ?, ?, ?, ?)",
              (game_id, datetime.now().isoformat(), game_id, status, file_path))
    conn.commit()
    conn.close()

def archive_to_duckdb(terminal_json, report_content):
    try:
        con = duckdb.connect("nba_analytics.duckdb")
        con.execute("CREATE TABLE IF NOT EXISTS terminal_archives (game_id TEXT, date DATE, data JSON, report_content TEXT, created_at TIMESTAMP)")
        
        # Check integrity
        # Insert
        con.execute("INSERT INTO terminal_archives VALUES (?, ?, ?, ?, ?)", 
                   (terminal_json['layer_1_meta']['game_id'], terminal_json['layer_1_meta']['date'], json.dumps(terminal_json), report_content, datetime.now()))
        con.close()
        print(f"✅ Archived Game {terminal_json['layer_1_meta']['game_id']} to DuckDB.")
    except Exception as e:
        print(f"⚠️ DuckDB Archive Error: {e}")

async def run_pipeline(game_id):
    print(f"\n🔥 [Matched Terminal View] Starting Report Gen for Game ID: {game_id}")
    log_status(game_id, "STARTED")

    # Step 1: Generate 7-Layer View
    try:
        print(f"   Step 1: Building 7-Layer Terminal View...")
        # Since module names starting with numbers are tricky to import, we use runpy or importlib
        import importlib.util
        spec = importlib.util.spec_from_file_location("terminal_view", "nba_data/pipeline/30_terminal_view.py")
        tv_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tv_module)
        
        terminal_data = await tv_module.generate_terminal_json(game_id)
        
        # Save JSON
        json_path = f"{TERMINAL_VIEW_DIR}/game_{game_id}.json"
        with open(json_path, 'w') as f:
            json.dump(terminal_data, f, indent=2)
        print(f"   ✅ JSON Generated: {json_path}")
    except Exception as e:
        print(f"   ❌ Failed to generate Terminal View: {e}")
        log_status(game_id, "FAILED_STEP_1")
        return

    # Step 2: Generate Report (with Retries)
    html_content = ""
    retry_count = 0
    max_retries = 2
    success = False

    import importlib.util
    spec_rep = importlib.util.spec_from_file_location("report_agent", "nba_data/pipeline/31_report_agent.py")
    agent_module = importlib.util.module_from_spec(spec_rep)
    spec_rep.loader.exec_module(agent_module)

    while retry_count <= max_retries:
        try:
            print(f"   Step 2: Analysis Agent (Attempt {retry_count+1})...")
            html_content = await agent_module.generate_report(terminal_data)
            success = True
            break
        except Exception as e:
            print(f"   ⚠️ Generation Failed: {e}")
            retry_count += 1
    
    if not success:
        print("   ⚠️ All retries failed. Using Fallback Template.")
        html_content = f"<h1>Analysis Unavailable</h1><p>The system could not generate a report for Game {game_id}.</p>"
        log_status(game_id, "PARTIAL_FAILURE")

    # Step 3: Save & Deliver
    try:
        html_path = f"{REPORT_DIR}/report_{game_id}.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"   ✅ HTML Saved: {html_path}")

        # Sync to Supabase
        if supabase:
            payload = {
                "date": terminal_data['layer_1_meta']['date'],
                "report_type": "TERMINAL_VIEW",
                "content": terminal_data, # We store the JSON source
                "metadata": {"html_report": html_content, "game_id": game_id},
                "updated_at": datetime.utcnow().isoformat()
            }
            # Insert logic via RPC or simple Table Insert if allowed
            # We used 'daily_reports' in previous step
            supabase.table("daily_reports").upsert(payload, on_conflict="date, report_type").execute()
            print("   ✅ Synced to Supabase Cloud.")

        # Archive DuckDB
        archive_to_duckdb(terminal_data, html_content)
        
        log_status(game_id, "COMPLETED", html_path)
        print(f"🚀 Mission Complete. Report Ready.\n")

    except Exception as e:
        print(f"   ❌ Delivery Failed: {e}")
        log_status(game_id, "FAILED_DELIVERY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game_id", required=True, help="NBA Game ID")
    args = parser.parse_args()

    init_sqlite()
    asyncio.run(run_pipeline(args.game_id))
