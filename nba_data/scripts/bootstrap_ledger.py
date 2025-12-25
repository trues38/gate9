
import duckdb
import os
import csv

DB_PATH = 'nba_sql.duckdb'
OUTPUT_CSV = 'g9_core_export/DATA/rdata_2025_26.csv'
TARGET_SEASON_START = '2025-10-01'

def bootstrap_ledger():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return

    con = duckdb.connect(DB_PATH)
    
    # Query: Select relevant columns for the daily ledger
    # We want a mix of identification + metrics
    # Note: 'rdata_treasury' has vast columns. We picked a subset for the "Ledger".
    # Or do we dump EVERYTHING? CSV with 100 cols is hard to read.
    # Let's dump the Essential G9 Metrics + Raw Stats.
    
    query = f"""
        SELECT 
            Date, 
            Team, 
            Opponent, 
            Location, 
            game_id,
            Points, 
            OpponentPoints,
            Pace_Sea as Pace,
            NetRtg_Sea as NetRtg,
            NetRtg_L10,
            Diff as RestDiff,
            days_since_last as RestDays,
            regime_headline -- Check if this exists?
        FROM rdata_treasury
        WHERE Date >= '{TARGET_SEASON_START}'
        ORDER BY Date DESC
    """
    
    try:
        # Check if regime_headline column exists, if not, remove from query
        cols = [c[0] for c in con.execute("DESCRIBE rdata_treasury").fetchall()]
        has_headline = 'regime_headline' in cols
        
        final_query = query.replace("regime_headline", "'' as regime_headline") if not has_headline else query
        
        print(f"🚀 Exporting 2025-26 Data to {OUTPUT_CSV}...")
        con.execute(f"COPY ({final_query}) TO '{OUTPUT_CSV}' (HEADER, DELIMITER ',')")
        print("✅ Export Complete.")
        
    except Exception as e:
        print(f"❌ Export Failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    # Ensure DIR exists
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    bootstrap_ledger()
