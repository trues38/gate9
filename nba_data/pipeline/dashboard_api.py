
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import duckdb
import subprocess
import os
from typing import List, Optional
from datetime import date

app = FastAPI(title="NBA Admin Dashboard API")

DB_PATH = "nba_analytics.duckdb"

# Pydantic Models
class OverrideRequest(BaseModel):
    entity_type: str
    entity_id: str
    field: str
    new_value: str
    notes: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "Database & API Operational"}

# ---------------------------------------------------------
# 1. STATUS BOARD (Health Checks)
# ---------------------------------------------------------
@app.get("/status/health")
def get_health_status():
    con = duckdb.connect(DB_PATH, read_only=True)
    today = date.today()
    
    # Check Lineups
    roster_count = con.execute(f"SELECT COUNT(*) FROM fact_rosters WHERE date = '{today}'").fetchone()[0]
    # Check Regimes
    regime_count = con.execute(f"SELECT COUNT(*) FROM fact_regimes WHERE date = '{today}'").fetchone()[0]
    
    con.close()
    
    return {
        "date": str(today),
        "lineups_synced": roster_count > 0,
        "lineup_player_count": roster_count,
        "regime_synced": regime_count > 0,
        "regime_team_count": regime_count,
        "db_status": "Healthy"
    }

# ---------------------------------------------------------
# 2. EXPLORE DATA
# ---------------------------------------------------------
@app.get("/data/rosters/{team_id}")
def get_roster(team_id: int):
    con = duckdb.connect(DB_PATH, read_only=True)
    today = date.today() # In production, maybe allow date param
    
    query = f"""
        SELECT player_name, is_starter, last_pts, status 
        FROM fact_rosters 
        WHERE team_id = {team_id} AND date = '{today}'
    """
    rows = con.execute(query).fetchall()
    con.close()
    
    return [{"name": r[0], "starter": r[1], "last_pts": r[2], "status": r[3]} for r in rows]

# ---------------------------------------------------------
# 3. ACTIONS (Triggers)
# ---------------------------------------------------------
@app.post("/actions/generate")
def trigger_generation(game_id: Optional[str] = None):
    # This invokes the batch runner
    # If game_id provided, we might need a modified runner, but for now run all
    try:
        if game_id:
             # run single
             cmd = f"python3 -c \"from nba_data.pipeline.unified_report_v2 import generate_report; generate_report('{game_id}')\""
        else:
             cmd = "python3 nba_data/pipeline/26_batch_runner.py"
             
        subprocess.Popen(cmd, shell=True) # Run in background
        return {"status": "Triggered", "command": cmd}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actions/override")
def apply_override(req: OverrideRequest):
    con = duckdb.connect(DB_PATH)
    con.execute("""
        INSERT INTO ops_overrides (target_date, entity_type, entity_id, field, new_value, notes)
        VALUES (CURRENT_DATE, ?, ?, ?, ?, ?)
    """, (req.entity_type, req.entity_id, req.field, req.new_value, req.notes))
    con.close()
    return {"status": "Override Applied"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
