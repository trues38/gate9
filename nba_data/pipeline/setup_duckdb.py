
import duckdb
import os

DB_PATH = "nba_analytics.duckdb"

def init_db():
    print(f"🦆 Initializing DuckDB at {DB_PATH}...")
    con = duckdb.connect(DB_PATH)
    
    # 1. DIM_TEAMS (Static Metadata)
    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_teams (
            team_id INTEGER PRIMARY KEY,
            name VARCHAR,
            abbreviation VARCHAR,
            conference VARCHAR,
            division VARCHAR
        )
    """)
    
    # 2. FACT_REGIMES (Daily Snapshots of Team State)
    # The "History" of Regimes. Primary Key: (team_id, date)
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_regimes (
            date TIMESTAMP,
            team_id INTEGER,
            momentum_score FLOAT,
            volatility_score FLOAT,
            regime_label VARCHAR,
            record VARCHAR,
            streak VARCHAR,
            PRIMARY KEY (date, team_id)
        )
    """)
    
    # 3. FACT_ROSTERS (Daily Lineup Snapshots)
    # Allows tracking "Was Booker playing on Dec 8?"
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_rosters (
            date TIMESTAMP,
            team_id INTEGER,
            player_name VARCHAR,
            is_starter BOOLEAN,
            last_pts INTEGER,
            status VARCHAR DEFAULT 'ACTIVE'
        )
    """)
    
    # 4. FACT_INJURIES (Daily Injury Report)
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_injuries (
            date TIMESTAMP,
            team_id INTEGER,
            player_name VARCHAR,
            status VARCHAR, -- 'OUT', 'QUESTIONABLE'
            description VARCHAR
        )
    """)
    
    # 5. OVERRIDES (Manual Corrections)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ops_overrides (
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            target_date TIMESTAMP,
            entity_type VARCHAR, -- 'PLAYER', 'TEAM'
            entity_id VARCHAR,
            field VARCHAR,
            new_value VARCHAR,
            notes VARCHAR
        )
    """)
    
    print("✅ Schema Created Successfully.")
    
    # Verify
    tables = con.execute("SHOW TABLES").fetchall()
    print("📋 Current Tables:")
    for t in tables:
        print(f"   - {t[0]}")
        
    con.close()

if __name__ == "__main__":
    init_db()
