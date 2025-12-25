
import duckdb
import pandas as pd
import os
import glob

# Config
DB_PATH = 'nba_sql.duckdb'
LEDGER_PATH = 'g9_core_export/DATA/rdata_2025_26.csv'

def sync_to_db():
    print("🚀 Starting Deep Sync: Ledger -> DuckDB Engine...")
    
    if not os.path.exists(DB_PATH) or not os.path.exists(LEDGER_PATH):
        print("❌ Missing DB or Ledger file.")
        return

    con = duckdb.connect(DB_PATH)
    
    # 1. Load Ledger
    df = pd.read_csv(LEDGER_PATH)
    print(f"📖 Ledger loaded: {len(df)} rows.")
    
    # 2. Identify New Rows
    # Simple check: what game_ids are already in DB?
    # Note: 'game_id' in DB is VARCHAR.
    try:
        existing_ids = set(x[0] for x in con.execute("SELECT game_id FROM rdata_treasury WHERE date >= '2025-10-01'").fetchall())
    except:
        existing_ids = set()
        
    # Filter new
    # df columns match Ledger: Date,Team,Opp,Location,game_id,Points...
    # DB columns: see schema.
    
    new_rows = df[~df['game_id'].astype(str).isin(existing_ids)]
    
    if new_rows.empty:
        print("✅ DB is already up to date.")
        con.close()
        return

    print(f"📥 Inserting {len(new_rows)} new rows into Engine...")
    
    # 3. Insert Raw Data
    # We need to map CSV columns to DB columns.
    # DB has many columns. We fill known ones, NULL others (to be calced).
    # DuckDB INSERT via Appender or SQL?
    # SQL INSERT with explicit column mapping is safest.
    
    for idx, row in new_rows.iterrows():
        # Prepare valid values
        # Schema check:
        # Date, Team, Points, Opponent, OpponentPoints, game_id, Location, Pace_Sea, NetRtg_Sea, regime_headline, Regime_Tag
        
        # Note: 'Pace' in CSV -> 'Pace_Sea' in DB? Or just filler? 
        # Actually in settle script we saved as Pace.
        
        sql = f"""
            INSERT INTO rdata_treasury (
                Date, Team, Points, Opponent, OpponentPoints, game_id, Location, 
                Pace_Sea, NetRtg_Sea, Diff, days_since_last, regime_headline, Regime_Tag
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?
            )
        """
        params = (
            row['Date'], row['Team'], row['Points'], row['Opponent'], row['OpponentPoints'], str(row['game_id']), row['Location'],
            row['Pace'], row['NetRtg'], row.get('RestDiff', 0), row.get('RestDays', 0), 
            row.get('regime_headline', ''), row.get('Regime_Tag', '')
        )
        
        try:
            con.execute(sql, params)
        except Exception as e:
            print(f"⚠️ Insert Error row {idx}: {e}")
            
    print("🔄 Recalculating Rolling Metrics (Window Functions)...")
    
    # 4. Advanced Metrics Recalculation (The "Deep" part)
    # We execute a massive update using Window Functions.
    # Logic: avg_P_4 (Pace Last 4) = AVG(Pace_Sea) OVER (PARTITION BY Team ORDER BY Date ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING)
    # Note: 'Pace_Sea' is the raw pace of that game in the DB context (Naming is weird but standard in legacy G9).
    
    # Example for Pace (avg_P_4)
    update_query = """
        UPDATE rdata_treasury
        SET 
            avg_P_4 = sub.avg_p4,
            avg_P_8 = sub.avg_p8,
            NetRtg_L10 = sub.avg_n10
        FROM (
            SELECT 
                game_id, Team,
                AVG(Pace_Sea) OVER (PARTITION BY Team ORDER BY Date ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) as avg_p4,
                AVG(Pace_Sea) OVER (PARTITION BY Team ORDER BY Date ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING) as avg_p8,
                AVG(NetRtg_Sea) OVER (PARTITION BY Team ORDER BY Date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as avg_n10
            FROM rdata_treasury
        ) sub
        WHERE rdata_treasury.game_id = sub.game_id
          AND rdata_treasury.Team = sub.Team
          AND rdata_treasury.Date >= '2025-10-01' -- Limit scope for speed
    """
    
    con.execute(update_query)
    
    print("✅ Deep Sync Complete. Rolling averages updated.")
    con.close()

if __name__ == "__main__":
    sync_to_db()
