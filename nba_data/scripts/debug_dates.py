import duckdb
try:
    con = duckdb.connect('nba_sql.duckdb', read_only=True)
    res = con.sql("SELECT Team, Date, Opponent FROM rdata_treasury LIMIT 3").fetchall()
    print("Rows:", res)
    
    # Check schema
    schema = con.sql("DESCRIBE rdata_treasury").fetchall()
    print("Schema:", schema)
except Exception as e:
    print(e)
