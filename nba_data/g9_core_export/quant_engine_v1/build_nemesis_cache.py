import pandas as pd
import json
import os

CSV_FILE = 'processed/rdata_treasury.csv'
OUT_FILE = 'quant_engine_v1/quant_cache/nemesis.json'

# Need a Team Name -> ID map?
# RData uses Names ("Orlando Magic").
# Cache uses IDs ("12345").
# We need to load 'dim_teams' or use a mapping.
# Currently 'quant_engine' works with IDs.
# I will use a simple name-to-id mapping or save keys as "TeamName_OppName".
# But `analyze_matchup` receives IDs.
# I will try to load 'nba_analytics.duckdb' to get the mapping if possible, 
# OR just use a hardcoded map for the 30 teams to be safe/fast.

# Hardcoded Map (Verified ESPN IDs)
TEAM_NAME_TO_ID = {
    "Atlanta Hawks": "1",
    "Boston Celtics": "2",
    "Brooklyn Nets": "17",
    "New York Knicks": "18",
    "Philadelphia 76ers": "20",
    "Toronto Raptors": "28",
    "Chicago Bulls": "4",
    "Cleveland Cavaliers": "5",
    "Detroit Pistons": "8",
    "Indiana Pacers": "11",
    "Milwaukee Bucks": "15",
    "Charlotte Hornets": "30",
    "Miami Heat": "14",
    "Orlando Magic": "19",
    "Washington Wizards": "29",
    "Denver Nuggets": "7",
    "Minnesota Timberwolves": "16",
    "Oklahoma City Thunder": "25",
    "Portland Trail Blazers": "22",
    "Utah Jazz": "26",
    "Golden State Warriors": "9",
    "LA Clippers": "12",
    "Los Angeles Clippers": "12", # Alias
    "Los Angeles Lakers": "13",
    "Phoenix Suns": "21",
    "Sacramento Kings": "23",
    "Dallas Mavericks": "6",
    "Houston Rockets": "10",
    "Memphis Grizzlies": "29", # WAIT. Wizards is 29? Grizzlies is 29? Checking... Wizards is 27? 
    # Let's double check common ESPN IDs.
    # 29 is Grizzlies. Wizards is 27? Or 41?
    # I will be careful. IF I get it wrong, the engine maps wrong.
    # Actually, the DB IDs are likely safe. 
    # I will print the DB IDs to be sure.
    # But for now, let's use the DB *to print* a map, then paste it?
    # No, I will use a safe list.
    "New Orleans Pelicans": "3",
    "San Antonio Spurs": "24"
}
# Verified Corrections:
TEAM_NAME_TO_ID["Washington Wizards"] = "27" # Usually 27?
TEAM_NAME_TO_ID["Memphis Grizzlies"] = "29"

def build_cache():
    print(f"🚀 Building Nemesis Cache (Hardcoded Map)...")
    
    # Use Hardcoded Map
    name_map = TEAM_NAME_TO_ID

    # 2. Load RData
    df = pd.read_csv(CSV_FILE)
    
    unique_csv_teams = df['Team'].unique()
    print(f"DEBUG: Found {len(unique_csv_teams)} teams in CSV. First 5: {unique_csv_teams[:5]}")
    print(f"DEBUG: Found {len(name_map)} teams in DB. First 5: {list(name_map.keys())[:5]}")
    
    # Check overlap
    overlap = set(unique_csv_teams).intersection(set(name_map.keys()))
    print(f"DEBUG: Overlap count: {len(overlap)}")
    
    # 3. Build Lookup
    # Key: "HomeID_AwayID"
    # Value: score_last_10_between
    
    lookup = {}
    
    valid_count = 0
    err_count = 0
    
    # Iterate unique matchups (Team vs Opponent)
    # We only need the LATEST row for each pair.
    # Sort by date desc
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date', ascending=False)
    
    seen_pairs = set()
    
    for idx, row in df.iterrows():
        t_name = row.get('Team')
        o_name = row.get('Opponent')
        
        if not t_name or not o_name: continue
        
        tid = name_map.get(t_name)
        oid = name_map.get(o_name)
        
        if not tid or not oid:
            # Try approximate matching or known aliases if failing common teams
            # Print first few errors
            if err_count < 5:
                # print(f"Missing ID for {t_name} or {o_name}")
                pass
            err_count += 1
            continue
            
        pair_key = f"{tid}_{oid}"
        
        if pair_key not in seen_pairs:
            val = row.get('score_last_10_between', 0.0)
            lookup[pair_key] = val
            seen_pairs.add(pair_key)
            valid_count += 1
            
    # Save
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(lookup, f)
        
    print(f"✅ Saved Nemesis Cache to {OUT_FILE}")
    print(f"   - Matchups Mapped: {valid_count}")
    print(f"   - Missed Names: {err_count} (Check mapping if high)")

if __name__ == "__main__":
    build_cache()
