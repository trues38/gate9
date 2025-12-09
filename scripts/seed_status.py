import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import random

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

# Initialize Supabase
supabase: Client = create_client(url, key)

print(f"Connecting to {url}...")

# --- V2 OPS CENTER DATA GENERATION (MOCK + DEBUG METADATA) ---

# 1. Data Integrity Monitor (With Maintenance Context)
integrity_monitor = [
    {
        "source": "News Feed", 
        "last_run": datetime.now().isoformat(), 
        "status": "SUCCESS", 
        "count": "132 articles", 
        "action": "news",
        "debug": {
            "pyscript": "nba_data/pipeline/04_crawl_stories.py",
            "key_check": "ESPN_API_KEY (Optional), OPENROUTER_API_KEY (Summaries)",
            "infra": "GitHub Action 'News Ingest'",
            "logs": "/logs/news_daemon.log",
            "common_error": "ESPN RSS structure change or Rate Limit (429)"
        }
    },
    {
        "source": "Stats & Standings", 
        "last_run": datetime.now().isoformat(), 
        "status": "SUCCESS", 
        "count": "30 teams", 
        "action": "stats",
        "debug": {
            "pyscript": "nba_data/pipeline/27_update_standings.py",
            "key_check": "None (Public HTML Parsing)",
            "infra": "GitHub Action 'Stats Sync'",
            "logs": "/logs/stats_update.log",
            "common_error": "Basketball-Reference DOM change"
        }
    },
    {
        "source": "Lineups", 
        "last_run": datetime.now().isoformat(), 
        "status": "SUCCESS", 
        "count": "142 players", 
        "action": "lineups",
        "debug": {
            "pyscript": "nba_data/pipeline/28_update_rosters.py",
            "key_check": "None (Rotowire Scraping)",
            "infra": "GitHub Action 'Roster Check'",
            "logs": "/logs/roster.log",
            "common_error": "Player Name Mismatch (e.g. Jr./III suffix)"
        }
    },
    {
        "source": "Injuries", 
        "last_run": datetime.now().isoformat(), 
        "status": "WARNING", 
        "count": "40/43 updated", 
        "action": "injuries",
        "debug": {
            "pyscript": "nba_data/pipeline/28_update_rosters.py (Injury Section)",
            "key_check": "None",
            "infra": "Combined with Lineups",
            "logs": "/logs/injury_monitor.log",
            "common_error": "Missing Player ID in master_map.json"
        }
    },
    {
        "source": "Regime Analysis", 
        "last_run": datetime.now().isoformat(), 
        "status": "SUCCESS", 
        "count": "30 teams", 
        "action": "regime",
        "debug": {
            "pyscript": "nba_data/pipeline/29_update_daily_regimes.py",
            "key_check": "DuckDB Connection",
            "infra": "Local / GitHub Runner",
            "logs": "/logs/regime_calc.log",
            "common_error": "Insufficient history data (need >5 games)"
        }
    },
    {
        "source": "Report Generator", 
        "last_run": datetime.now().isoformat(), 
        "status": "FAILED", 
        "count": "8/10 done", 
        "action": "reports",
        "debug": {
            "pyscript": "generate_report.py (Orchestrator)",
            "key_check": "OPENROUTER_API_KEY (DeepSeek), SUPABASE_URL",
            "infra": "Batch Runner",
            "logs": "/logs/batch_reports.log",
            "common_error": "LLM Context Limit Exceeded or 401 Auth Error"
        }
    },
    {
        "source": "DB Sync", 
        "last_run": datetime.now().isoformat(), 
        "status": "SUCCESS", 
        "count": "-", 
        "action": "sync",
        "debug": {
            "pyscript": "nba_ops_pipeline.py (Sync Block)",
            "key_check": "SUPABASE_SERVICE_ROLE_KEY",
            "infra": "Final Stage Pipeline",
            "logs": "/logs/sync.log",
            "common_error": "Network Timeout / Schema Mismatch"
        }
    },
]

# 2. Error Center
error_logs = [
    {"timestamp": "04:23", "module": "Report", "message": "TypeError: NoneType object is not subscriptable", "id": "err_1", "trace": "File 'generate_report.py', line 62, in <module>\nKeyError: 'game_meta'"},
    {"timestamp": "03:55", "module": "Injuries", "message": "Player ID 4402 missing in master map", "id": "err_2", "trace": "File 'map_tickers.py', line 102\nException: ID 4402 not found"},
    {"timestamp": "03:50", "module": "News", "message": "Parsing failure on espn.com/nba/story?id=...", "id": "err_3", "trace": "File 'crawl.py', line 88\nSoup elements not found"},
]

# 4. Recentness Bar (Percentage)
recentness = {
    "news": 98,
    "lineups": 78,
    "injuries": 60,
    "stats": 90,
    "odds": 100,
    "regime": 100,
    "reports": 70
}

# 5. Latest Snapshots
snapshots = [
    {"game": "BOS@TOR", "lineup": "OK", "injuries": "2 OUT", "referee": "Zarba", "regime": "Calculated", "report": "Open"},
    {"game": "DEN@CHA", "lineup": "OK", "injuries": "OK", "referee": "Brothers", "regime": "Failed", "report": "Retry"},
    {"game": "DAL@MEM", "lineup": "Missing", "injuries": "OK", "referee": "Crew-X", "regime": "Pending", "report": "-"},
]

# 6. System Health
system_health = [
    {"component": "Vercel Build", "status": "OK", "details": "2 min ago"},
    {"component": "GitHub Sync", "status": "OK", "details": "Synced"},
    {"component": "DuckDB", "status": "OK", "details": "Connected"},
    {"component": "SQLite", "status": "OK", "details": "Active"},
    {"component": "OpenRouter LLM", "status": "WARNING", "details": "1 failed attempt"},
    {"component": "ESPN API", "status": "OK", "details": "Stable"},
    {"component": "NFL Odds API", "status": "ERROR", "details": "Rate-limited"},
]


# Construct Full V2 Payload
status_payload = {
    "last_run_status": "OPS_V2_ACTIVE",
    "updated_at": datetime.utcnow().isoformat(),
    "lineups_updated": True, 
    "regimes_updated": True,
    "processed_count": 0,
    "last_run_log": json.dumps({
        "v2_enabled": True,
        "integrity_monitor": integrity_monitor,
        "error_logs": error_logs,
        "recentness": recentness,
        "snapshots": snapshots,
        "system_health": system_health,
        "reason": "OPS Center V2 (Traceback Enhanced)"
    })
}

# Insert
data, count = supabase.table("admin_system_status").insert(status_payload).execute()

print("✅ Seeded 'OPS CENTER V2' with Debug Metadata.")
