
import duckdb
import json
import datetime
from pathlib import Path

DB_PATH = "nba_analytics.duckdb"
DATA_DIR = Path("nba_data")
TODAY = datetime.date.today()

def migrate():
    print(f"📦 Migrating JSON Data to DuckDB ({DB_PATH})...")
    con = duckdb.connect(DB_PATH)
    
    # 1. TEAM REGIMES (Metadata + Snapshot)
    regime_path = DATA_DIR / "regimes" / "team_regimes.json"
    if regime_path.exists():
        with open(regime_path) as f:
            teams = json.load(f)
            
        print(f"   Processing {len(teams)} teams from team_regimes.json...")
        
        for t in teams:
            tid = t.get('team_id')
            name = t.get('team_name')
            
            # Upsert Dimension
            # (In production, use INSERT OR IGNORE, but DuckDB generic SQL:)
            count = con.execute(f"SELECT COUNT(*) FROM dim_teams WHERE team_id = {tid}").fetchone()[0]
            if count == 0:
                con.execute("INSERT INTO dim_teams VALUES (?, ?, ?, ?, ?)", 
                           (tid, name, t.get('abbreviation', name[:3].upper()), 'Unknown', 'Unknown'))
            
            # Insert Fact (Snapshot)
            # Remove existing for today to prevent dupes during dev
            con.execute(f"DELETE FROM fact_regimes WHERE team_id = {tid} AND date = '{TODAY}'")
            
            con.execute("""
                INSERT INTO fact_regimes VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                TODAY, 
                tid, 
                t.get('regime', {}).get('momentum_score', 0),
                t.get('regime', {}).get('volatility_score', 0),
                t.get('regime', {}).get('label', 'Unknown'),
                t.get('record', '0-0'),
                t.get('streak', '0')
            ))
            
    # 2. CURRENT ROSTERS (Live Lineups)
    roster_path = DATA_DIR / "regimes" / "current_regimes.json"
    if roster_path.exists():
        with open(roster_path) as f:
            players = json.load(f)
            
        print(f"   Processing {len(players)} active players from current_regimes.json...")
        
        # Clear today's roster snapshot
        con.execute(f"DELETE FROM fact_rosters WHERE date = '{TODAY}'")
        
        for p in players:
            con.execute("""
                INSERT INTO fact_rosters VALUES (?, ?, ?, ?, ?, ?)
            """, (
                TODAY,
                p.get('team_id'),
                p.get('name'),
                p.get('starter', False),
                p.get('last_pts', 0),
                'ACTIVE'
            ))
            
    con.close()
    print("✅ Migration Complete.")

if __name__ == "__main__":
    migrate()
