
import duckdb
import os

DB_PATH = 'nba_sql.duckdb'

def check_recency():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return

    con = duckdb.connect(DB_PATH)
    
    # 1. List Tables
    tables = con.execute("SHOW TABLES").fetchall()
    print(f"📂 Tables found: {[t[0] for t in tables]}")
    
    # 2. Check Recency in likely tables
    target_tables = ['rdata', 'nba_games', 'team_stats', 'rdata_treasury']
    
    for tbl in tables:
        tbl_name = tbl[0]
        if tbl_name in target_tables or 'data' in tbl_name:
            try:
                # Check column names first to find 'date' or 'game_date'
                cols = con.execute(f"DESCRIBE {tbl_name}").fetchall()
                col_names = [c[0] for c in cols]
                
                date_col = next((c for c in col_names if 'date' in c.lower()), None)
                
                if date_col:
                    max_date = con.execute(f"SELECT MAX({date_col}) FROM {tbl_name}").fetchone()[0]
                    count = con.execute(f"SELECT COUNT(*) FROM {tbl_name}").fetchone()[0]
                    print(f"📅 Table '{tbl_name}': Max Date = {max_date} (Rows: {count})")
                    
                    if tbl_name == 'rdata_treasury':
                        print(f"\n📋 Schema for {tbl_name}:")
                        for c in cols:
                            print(f"  - {c[0]} ({c[1]})")
                else:
                    print(f"⚠️ Table '{tbl_name}': No date column found.")
            except Exception as e:
                print(f"❌ Error checking {tbl_name}: {e}")
                
    con.close()

if __name__ == "__main__":
    check_recency()
