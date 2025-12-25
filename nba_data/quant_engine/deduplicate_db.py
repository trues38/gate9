
import duckdb

DB_PATH = "/Users/js/g9/nba_analytics.duckdb"

def deduplicate():
    con = duckdb.connect(DB_PATH)
    print("Connecting to DB...")
    
    # Check count before
    count_before = con.execute("SELECT COUNT(*) FROM fact_gamelogs").fetchone()[0]
    print(f"Rows Before: {count_before}")
    
    # Simple Deduplication: Create temp table with distinct rows, drop old, rename.
    # Since we have no unique ID other than compound (game_id, person_id).
    # We will use that.
    
    print("Deduplicating...")
    con.execute("""
        CREATE TABLE fact_gamelogs_temp AS
        SELECT DISTINCT * FROM fact_gamelogs
    """)
    
    count_temp = con.execute("SELECT COUNT(*) FROM fact_gamelogs_temp").fetchone()[0]
    print(f"Rows After Deduplication (Temp): {count_temp}")
    
    if count_temp < count_before:
        con.execute("DROP TABLE fact_gamelogs")
        con.execute("ALTER TABLE fact_gamelogs_temp RENAME TO fact_gamelogs")
        print("Success: Duplicates removed.")
    else:
        print("No duplicates found (or distinct failed).")
        con.execute("DROP TABLE fact_gamelogs_temp")
        
    con.close()

if __name__ == "__main__":
    deduplicate()
