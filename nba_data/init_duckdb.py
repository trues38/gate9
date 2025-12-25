import duckdb
import pandas as pd
import os

DB_PATH = "nba_sql.duckdb"
CSV_PATH = "processed/rdata_treasury.csv"

def init_db():
    print(f"🚀 Initializing DuckDB at {DB_PATH}...")
    
    # Connect (Current directory)
    con = duckdb.connect(DB_PATH)
    
    # 1. Drop if exists (Fresh Start)
    con.execute("DROP TABLE IF EXISTS rdata_treasury")
    
    # 1. Drop if exists (Fresh Start)
    con.execute("DROP TABLE IF EXISTS rdata_treasury")
    
    # OLD LOGIC REMOVED
    # 2. Pandas Load & Standardize logic executes below...
    
    # 4. Verification
    # count = con.execute("SELECT COUNT(*) FROM rdata_treasury").fetchone()[0] # This line is no longer needed here as we're loading via pandas
    print(f"📥 Loading RData Treasury: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    # --- USER PROVIDED STANDARDIZATION ---
    def standardize_team_names(df, team_col='Team'):
        nba_mapper = {
            'Atlanta Hawks': 'ATL', 'Atlanta': 'ATL', 'Hawks': 'ATL',
            'Boston Celtics': 'BOS', 'Boston': 'BOS', 'Celtics': 'BOS',
            'Brooklyn Nets': 'BKN', 'Brooklyn': 'BKN', 'Nets': 'BKN',
            'Charlotte Hornets': 'CHA', 'Charlotte': 'CHA', 'Hornets': 'CHA',
            'Chicago Bulls': 'CHI', 'Chicago': 'CHI', 'Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE', 'Cleveland': 'CLE', 'Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL', 'Dallas': 'DAL', 'Mavericks': 'DAL',
            'Denver Nuggets': 'DEN', 'Denver': 'DEN', 'Nuggets': 'DEN',
            'Detroit Pistons': 'DET', 'Detroit': 'DET', 'Pistons': 'DET',
            'Golden State Warriors': 'GSW', 'Golden State': 'GSW', 'Warriors': 'GSW',
            'Houston Rockets': 'HOU', 'Houston': 'HOU', 'Rockets': 'HOU',
            'Indiana Pacers': 'IND', 'Indiana': 'IND', 'Pacers': 'IND',
            'Los Angeles Clippers': 'LAC', 'L.A. Clippers': 'LAC', 'Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL', 'L.A. Lakers': 'LAL', 'Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM', 'Memphis': 'MEM', 'Grizzlies': 'MEM',
            'Miami Heat': 'MIA', 'Miami': 'MIA', 'Heat': 'MIA',
            'Milwaukee Bucks': 'MIL', 'Milwaukee': 'MIL', 'Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN', 'Minnesota': 'MIN', 'Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP', 'New Orleans': 'NOP', 'Pelicans': 'NOP',
            'New York Knicks': 'NYK', 'New York': 'NYK', 'Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC', 'Oklahoma City': 'OKC', 'Thunder': 'OKC',
            'Orlando Magic': 'ORL', 'Orlando': 'ORL', 'Magic': 'ORL',
            'Philadelphia 76ers': 'PHI', 'Philadelphia': 'PHI', '76ers': 'PHI',
            'Phoenix Suns': 'PHX', 'Phoenix': 'PHX', 'Suns': 'PHX',
            'Portland Trail Blazers': 'POR', 'Portland': 'POR', 'Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC', 'Sacramento': 'SAC', 'Kings': 'SAC',
            'San Antonio Spurs': 'SAS', 'San Antonio': 'SAS', 'Spurs': 'SAS',
            'Toronto Raptors': 'TOR', 'Toronto': 'TOR', 'Raptors': 'TOR',
            'Utah Jazz': 'UTA', 'Utah': 'UTA', 'Jazz': 'UTA',
            'Washington Wizards': 'WAS', 'Washington': 'WAS', 'Wizards': 'WAS'
        }
        df[team_col] = df[team_col].map(nba_mapper).fillna(df[team_col])
        return df

    print("🔎 Standardizing Team Names to 3-Letter Codes...")
    if 'Team' in df.columns: 
        df = standardize_team_names(df, 'Team')
    if 'Opponent' in df.columns:
        df = standardize_team_names(df, 'Opponent')
        
    print(f"✅ Data Loaded. Rows: {len(df)}")

    # Load the processed DataFrame into DuckDB
    con.execute("CREATE TABLE rdata_treasury AS SELECT * FROM df")

    # 3. Create Indexes for Performance (Moved here)
    print("⚡ Creating Indexes...")
    con.execute("CREATE INDEX idx_team_date ON rdata_treasury (Team, Date)")
    con.execute("CREATE INDEX idx_game_id ON rdata_treasury (game_id)")

    # 4. Verification (re-check count after loading into DB)
    count = con.execute("SELECT COUNT(*) FROM rdata_treasury").fetchone()[0]
    print(f"✅ Migration Complete. Total Rows: {count}")
    
    # 5. Show Schema
    print("\n[Schema]")
    print(con.execute("DESCRIBE rdata_treasury").df().to_string())
    
    con.close()

if __name__ == "__main__":
    init_db()
