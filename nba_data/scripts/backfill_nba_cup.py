import pandas as pd
import numpy as np
import duckdb

# 1. Load Treasury
treasury_path = 'processed/rdata_treasury.csv'
df = pd.read_csv(treasury_path)
print(f"Loaded Treasury: {len(df)} rows")

# 2. Define New Games (Dec 10 & 11)
# Data fetched via Browser Subagent
new_games = [
    # Dec 10: MIA @ ORL (ORL 117-108) | Pace: 103.2
    # ORL (Home)
    {'Date': '2025-12-10', 'Team': 'ORL', 'Opponent': 'MIA', 'Points': 117, 'OpponentPoints': 108, 'Location': 'Home', 'Pace': 103.2, 'game_id': '0022501201'},
    # MIA (Away)
    {'Date': '2025-12-10', 'Team': 'MIA', 'Opponent': 'ORL', 'Points': 108, 'OpponentPoints': 117, 'Location': 'Away', 'Pace': 103.2, 'game_id': '0022501201'},
    
    # Dec 10: NYK @ TOR (NYK 117-101) | Pace: 96.12
    # NYK (Away) - Winner
    {'Date': '2025-12-10', 'Team': 'NYK', 'Opponent': 'TOR', 'Points': 117, 'OpponentPoints': 101, 'Location': 'Away', 'Pace': 96.12, 'game_id': '0022501203'},
    # TOR (Home) - Loser
    {'Date': '2025-12-10', 'Team': 'TOR', 'Opponent': 'NYK', 'Points': 101, 'OpponentPoints': 117, 'Location': 'Home', 'Pace': 96.12, 'game_id': '0022501203'},

    # Dec 11: PHX @ OKC (OKC 138-89) | Pace: 103.88
    # OKC (Home) - Winner
    {'Date': '2025-12-11', 'Team': 'OKC', 'Opponent': 'PHX', 'Points': 138, 'OpponentPoints': 89, 'Location': 'Home', 'Pace': 103.88, 'game_id': '0022501204'},
    # PHX (Away) - Loser
    {'Date': '2025-12-11', 'Team': 'PHX', 'Opponent': 'OKC', 'Points': 89, 'OpponentPoints': 138, 'Location': 'Away', 'Pace': 103.88, 'game_id': '0022501204'},
    
    # Dec 11: SAS @ LAL (SAS 132-119) | Pace: 103.48
    # SAS (Away) - Winner
    {'Date': '2025-12-11', 'Team': 'SAS', 'Opponent': 'LAL', 'Points': 132, 'OpponentPoints': 119, 'Location': 'Away', 'Pace': 103.48, 'game_id': '0022501205'},
    # LAL (Home) - Loser
    {'Date': '2025-12-11', 'Team': 'LAL', 'Opponent': 'SAS', 'Points': 119, 'OpponentPoints': 132, 'Location': 'Home', 'Pace': 103.48, 'game_id': '0022501205'}
]

# 3. Create DataFrame
new_df = pd.DataFrame(new_games)

# 4. Map Columns to Treasury Schema
# Treasury Cols: Date,Team,odds,Points,Opponent,OpponentPoints,Attend.,LOG,temporada,hour,weekday,month,local,Team_Zone,Opponent_Zone,V,V_o...
# Key Mappings:
# LOG -> Pace
# local -> 1 (Home) / 0 (Away)
# V -> 1 (Win) / 0 (Loss)

# Fill Missing Cols with Defaults
# Note: Rolling avgs (avg_V_4 etc) will be null, but that is OK for Treasury historical record. 
# Feature Calculation script re-calculates them if needed, or we just need the Raw record for NEXT game calculation.

# Map 'Team' to Full Names if Treasury uses Full Names (It does: 'Atlanta Hawks')
# Need a map.
team_map = {
    'ORL': 'Orlando Magic', 'MIA': 'Miami Heat',
    'NYK': 'New York Knicks', 'TOR': 'Toronto Raptors',
    'OKC': 'Oklahoma City Thunder', 'PHX': 'Phoenix Suns',
    'SAS': 'San Antonio Spurs', 'LAL': 'Los Angeles Lakers'
}
new_df['Team'] = new_df['Team'].map(team_map)
new_df['Opponent'] = new_df['Opponent'].map(team_map)
new_df['LOG'] = new_df['Pace'] # Pace goes to LOG
new_df['local'] = new_df['Location'].apply(lambda x: 1 if x == 'Home' else 0)
new_df['V'] = np.where(new_df['Points'] > new_df['OpponentPoints'], 1.0, 0.0)
new_df['year'] = 2025
new_df['temporada'] = '2024-25' # or whatever schema uses

# Append
# First, remove any existing rows for these Date/Team combos to avoid dupes (and ensure ID update)
for new_game in new_games:
    d = new_game['Date']
    t = new_game['Team']
    df = df[~((df['Date'] == d) & (df['Team'] == t))]

final_df = pd.concat([df, new_df], ignore_index=True)
print(f"New Treasury Size: {len(final_df)} rows")

# 5. Save
final_df.to_csv(treasury_path, index=False)
print("Saved to processed/rdata_treasury.csv")

# 6. Re-init DuckDB
con = duckdb.connect('nba_sql.duckdb')
con.execute("DROP TABLE IF EXISTS rdata_treasury")
# Force temporada to VARCHAR to avoid type casting errors (some are 2009.0, some 2024-25)
con.execute(f"CREATE TABLE rdata_treasury AS SELECT * FROM read_csv_auto('{treasury_path}', sample_size=-1, all_varchar=1)")
# Now convert critical numerical columns back to Double if needed?
# Actually RDataEngine casts them on query usually, OR we can cast herein.
# But for safety, let's keep it robust. The engine queries need numeric Points/OppPoints.
# Let's try to load with explicit types for critical ones or just trust DuckDB's all_varchar=0 but with explicit override for temporada.

con.execute(f"CREATE TABLE rdata_treasury_temp AS SELECT * FROM read_csv_auto('{treasury_path}', sample_size=-1, types={{'temporada': 'VARCHAR', 'Date': 'VARCHAR'}})")
con.execute("DROP TABLE IF EXISTS rdata_treasury")
con.execute("ALTER TABLE rdata_treasury_temp RENAME TO rdata_treasury")

con.execute("CREATE INDEX idx_team ON rdata_treasury(Team)")
con.execute("CREATE INDEX idx_date ON rdata_treasury(Date)")
print("DuckDB Re-initialized.")
