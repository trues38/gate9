import duckdb

def check_db():
    try:
        con = duckdb.connect('nba_analytics.duckdb')
        
        tables = [x[0] for x in con.sql('SHOW TABLES').fetchall()]
        print(f"Tables Found: {tables}")
        
        counts = {
            "fact_game": "SELECT COUNT(*) FROM fact_game",
            "fact_game_final": "SELECT COUNT(*) FROM fact_game WHERE status='STATUS_FINAL'", 
            "fact_boxscore": "SELECT COUNT(*) FROM fact_boxscore",
            "fact_team_stats": "SELECT COUNT(*) FROM fact_team_stats",
            "fact_injury": "SELECT COUNT(*) FROM fact_injury"
        }
        
        for name, query in counts.items():
            if name.startswith("fact_game") or "fact_injury" in name or name in tables:
                try:
                    # For injury check if table exists first if not in tables list logic is weak
                    # But simpler:
                    if "fact_injury" in name and "fact_injury" not in tables:
                         print(f"[ ] {name}: TABLE MISSING")
                         continue
                         
                    cnt = con.sql(query).fetchone()[0]
                    print(f"[*] {name}: {cnt}")
                except Exception as e:
                    print(f"[!] {name}: Error {e}")
            else:
                 print(f"[ ] {name}: TABLE MISSING")
                 
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_db()
