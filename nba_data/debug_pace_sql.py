import duckdb

def debug_sql():
    con = duckdb.connect('nba_sql.duckdb', read_only=True)
    
    team = "Indiana Pacers"
    date = "2025-12-14"
    
    print(f"Checking history for {team} before {date}...")
    
    # Check Count
    count = con.execute("SELECT count(*) FROM rdata_treasury WHERE Team = ? AND Date < ?", [team, date]).fetchone()[0]
    print(f"Row Count: {count}")
    
    if count > 0:
        # Check Values
        res = con.execute("""
            SELECT Points, OpponentPoints, Date 
            FROM rdata_treasury 
            WHERE Team = ? AND Date < ? 
            ORDER BY Date DESC LIMIT 5
        """, [team, date]).fetchall()
        print("Last 5 Games:")
        for r in res:
            print(r)
            
        # Check Exact CTE Query
        query = """
            WITH hist AS (
                SELECT Points, OpponentPoints, Date, (Points - OpponentPoints) as Margin
                FROM rdata_treasury 
                WHERE Team = ? AND Date < ? 
                ORDER BY Date DESC
            )
            SELECT 
                (SELECT (avg(Points) + avg(OpponentPoints))/2 FROM (SELECT Points, OpponentPoints FROM hist LIMIT 32)) as Pace_Sea
        """
        pace_cte = con.execute(query, [team, date]).fetchone()[0]
        print(f"CTE Pace_Sea: {pace_cte}")
    else:
        print("❌ No history found! Check Team Name exact match or Date format.")
        
        # Check distinct teams to see if name matches
        teams = con.execute("SELECT DISTINCT Team FROM rdata_treasury WHERE Team LIKE '%Pacers%'").fetchall()
        print(f"Did you mean: {teams}")

if __name__ == "__main__":
    debug_sql()
