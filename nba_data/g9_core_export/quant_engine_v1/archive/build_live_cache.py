import pandas as pd
import json
import os

FEATURES_PATH = "processed/features_2025.csv"
CACHE_DIR = "quant_engine_v1/quant_cache"

def build_live_cache():
    print("🚀 Building Live Caches (Momentum & Nemesis) from Features 2025...")
    
    if not os.path.exists(FEATURES_PATH):
        print(f"❌ Features file not found: {FEATURES_PATH}")
        return

    df = pd.read_csv(FEATURES_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Load Team Map
    with open("quant_engine_v1/team_map.json", "r") as f:
        team_map = json.load(f)
        
    # Helper to get ID
    def get_id(name):
        return team_map.get(name) or team_map.get(name.replace("LA ", "Los Angeles "))

    # 1. Momentum Cache (Latest avg_V_4 per Team)
    df_sorted = df.sort_values(['Team', 'Date'])
    latest_team = df_sorted.groupby('Team').tail(1)
    
    # 2. Team Stats Cache (Power, Volatility, Pace)
    # Replaces old multiple JSONs with one unified source
    team_stats_cache = {}
    for _, row in latest_team.iterrows():
        tid = get_id(row['Team'])
        if not tid: continue
        
        team_stats_cache[str(tid)] = {
            'net_rating': row.get('NetRtg_Sea', 0.0),
            'net_rating_l10': row.get('NetRtg_L10', 0.0),
            'volatility': row.get('Vol_Sea', 10.0),
            'pace': row.get('Pace_Sea', 98.0)
        }
    
    with open(f"{CACHE_DIR}/team_stats_live.json", 'w') as f:
        json.dump(team_stats_cache, f, indent=2)
    print(f"✅ Team Stats Cache saved ({len(team_stats_cache)} teams).")

    # 3. Momentum Cache (Latest avg_V_4 per Team)
    momentum_cache = {}
    for _, row in latest_team.iterrows():
        tid = get_id(row['Team'])
        if not tid: continue
            
        momentum_cache[str(tid)] = {
            'avg_V_4': row.get('avg_V_4', 0.5),
            'last_date': str(row['Date']),
            'days_since_last': row.get('days_since_last', 3)
        }
        
    with open(f"{CACHE_DIR}/momentum_live.json", 'w') as f:
        json.dump(momentum_cache, f, indent=2)
    print(f"✅ Momentum Cache saved ({len(momentum_cache)} teams).")

    # 4. Nemesis Cache
    latest_pair = df_sorted.groupby(['Team', 'Opponent']).tail(1)
    nemesis_cache = {}
    for _, row in latest_pair.iterrows():
        tid = get_id(row['Team'])
        oid = get_id(row['Opponent'])
        if not tid or not oid: continue
        
        key = f"{tid}_{oid}"
        nemesis_cache[key] = row['score_last_10_between']
        
    with open(f"{CACHE_DIR}/nemesis_live.json", 'w') as f:
        json.dump(nemesis_cache, f, indent=2)
    print(f"✅ Nemesis Cache saved ({len(nemesis_cache)} pairs).")

if __name__ == "__main__":
    os.makedirs(CACHE_DIR, exist_ok=True)
    build_live_cache()
