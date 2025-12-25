
import duckdb
import pandas as pd
# from tabulate import tabulate # Disabled to avoid dependency error
import os

DB_PATH = "nba_analytics.duckdb"

LAYERS = {
    "1. Game Context": ["dim_schedule", "dim_games", "game_schedule"],
    "2. Team Regime": ["fact_regimes", "team_vectors"],
    "3. Player Regime": ["fact_player_regimes", "player_vectors"],
    "4. Roster": ["fact_rosters", "fact_injuries"],
    "5. Referee": ["fact_ref_regimes", "fact_referees"],
    "6. Narrative": ["fact_news", "fact_story_vectors"],
    "7. Market Odds": ["market_odds", "line_movement"]
}

def check_status():
    print(f"🏥 Checking 7-Layer Intelligence Stack in {DB_PATH}...\n")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return

    con = duckdb.connect(DB_PATH, read_only=True)
    existing_tables = [t[0] for t in con.sql("SHOW TABLES").fetchall()]
    
    report = []
    
    for layer_name, tables in LAYERS.items():
        layer_status = "❌ MISSING"
        details = []
        
        found_any = False
        row_counts = []
        
        for t in tables:
            if t in existing_tables:
                found_any = True
                try:
                    count = con.sql(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    row_counts.append(f"{t}: {count} rows")
                except:
                    row_counts.append(f"{t}: Error")
            else:
                pass
                
        if found_any:
            layer_status = "✅ ACTIVE"
            if not row_counts:
                 layer_status = "⚠️ EMPTY"
        else:
             layer_status = "❌ MISSING"
             
        report.append({
            "Layer": layer_name,
            "Status": layer_status,
            "Details": ", ".join(row_counts) if row_counts else "No tables found"
        })
        
    con.close()
    
    # Print Table
    print(f"{'LAYER':<25} | {'STATUS':<10} | {'DETAILS'}")
    print("-" * 70)
    for r in report:
        print(f"{r['Layer']:<25} | {r['Status']:<10} | {r['Details']}")
    print("-" * 70)

if __name__ == "__main__":
    check_status()
