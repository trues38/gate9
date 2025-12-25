import duckdb
import os

DB_PATH = 'nba_sql.duckdb'
CSV_PATH = 'processed/rdata_treasury.csv'

def reinit_db():
    print(f"🔄 Re-initializing DuckDB Treasury from {CSV_PATH}...")
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ Critical: {CSV_PATH} not found.")
        return

    con = duckdb.connect(DB_PATH)
    
    try:
        # Drop existing
        con.execute("DROP TABLE IF EXISTS rdata_treasury")
        
        # Create from CSV (Force string for safe loading, then cast if needed or rely on auto)
        # Using explicit types for critical columns to ensure schema stability
        print("  creating table...")
        
        
        sql = f"""
            CREATE TABLE rdata_treasury AS 
            SELECT * FROM read_csv_auto('{CSV_PATH}', sample_size=-1, types={{'Date': 'VARCHAR'}})
        """
        con.execute(sql)
        
        # Verify count
        count = con.execute("SELECT COUNT(*) FROM rdata_treasury").fetchone()[0]
        print(f"✅ Table 'rdata_treasury' created with {count} rows.")
        
        # Create Indices
        print("  creating indices...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_team ON rdata_treasury(Team)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_date ON rdata_treasury(Date)")
        
    except Exception as e:
        print(f"❌ DB Init Failed: {e}")
    finally:
        con.close()
        print("Done.")

if __name__ == "__main__":
    reinit_db()
