
import chromadb
import duckdb
import pandas as pd
import json
import os
import sys
from tqdm import tqdm

sys.path.append(os.getcwd())

def build_master_index():
    print("🧹 Starting Phase 34: The Semantic Reboot (Master Index Builder)")
    
    # 1. Load Semantic Memory (Chroma)
    # 1. Load Known Narrative Map (The Linker)
    print("🗺️ Loading Narrative Mapping (Universal Archive)...")
    try:
        with open("processed/universal_narrative_archive.json", "r") as f:
            archive_data = json.load(f)
        # Create Map: Date_Team -> Game_ID
        # Normalized Key: YYYY-MM-DD_Team
        
        id_map = {}
        headline_map = {} 
        body_map = {} # New
        semantic_flags = {}
        
        for item in archive_data:
            # Extract Team from quant_data if missing at top level
            team_name = item.get('team')
            if not team_name:
                q = item.get('quant_data')
                if q:
                    team_name = q.get('team')
            
            if team_name and item.get('date'):
                # Normalize Date to YYYY-MM-DD (just in case)
                d_str = str(item.get('date')).split()[0]
                key = f"{d_str}_{team_name}"
                gid = item.get('game_id')
                id_map[key] = gid
                headline_map[gid] = item.get('story_headline', "No Headline Found") 
                body_map[gid] = item.get('story_body', "") # Capture Body
                semantic_flags[gid] = True
            
        print(f"✅ Loaded {len(id_map)} Mapped Games from Archive.")
    except Exception as e:
        print(f"⚠️ Could not load Universal Archive: {e}")
        id_map = {}
        headline_map = {}
        body_map = {}
        semantic_flags = {}

    # 2. Load Quantitative Reality (DuckDB) - The Base 37k
    print("📊 Accessing Quantitative Treasury (DuckDB)...")
    con = duckdb.connect("nba_sql.duckdb", read_only=True)
    
    # Get Data since ~2013 to get approx 10k games
    # And ensure we have basic stats
    query = """
        SELECT 
            game_id as duck_key,
            date, 
            team, 
            opponent, 
            odds, 
            Points,
            OpponentPoints,
            avg_V_8 as momentum_proxy,
            days_since_last as rest_days
        FROM rdata_treasury 
        WHERE date >= '2014-10-01'
    """
    
    df_quant = con.execute(query).fetchdf()
    con.close()
    
    # Normalize Columns to lower case
    df_quant.columns = [c.lower() for c in df_quant.columns]
    print(f"DEBUG: Data Columns: {df_quant.columns.tolist()}")
    
    if len(df_quant) == 0:
        print("❌ CRITICAL: No data found in DuckDB.")
        return

    print(f"✅ Loaded {len(df_quant)} Base Games (Post-2014) from Treasury.")

    # 3. Enrich and Standardize
    print("🔗 Linking & Calculating Metrics...")
    
    final_records = []
    
    def calc_implied_prob(odds):
        try:
            val = float(odds)
            if val > 1.0: return 1.0 / val
            return 0.5
        except: return 0.5
        
    def get_result(row):
        try:
            diff = row['points'] - row['opponentpoints']
            return 'Win' if diff > 0 else 'Loss'
        except: return 'Unknown'
        
    first_n = 5
    counter = 0
    for index, row in tqdm(df_quant.iterrows(), total=len(df_quant)):
        # Construct Key to match Archive
        d = str(row['date'])
        t = str(row['team'])
        key = f"{d}_{t}"
        
        # Determine Game ID
        # Use Official ID if mapped, else Generate one
        official_id = id_map.get(key)
        
        # Calculate Metrics
        prob = calc_implied_prob(row['odds'])
        mom = float(row['momentum_proxy']) if pd.notnull(row['momentum_proxy']) else 0.0
        
        # Fake Edge Logic (Archetype)
        edge = round((prob * 100) + (mom * 5), 1)
        
        # Flow
        flow = "STABLE"
        if mom > 0.5: flow = "STRONG_UP"
        elif mom < -0.5: flow = "CRASH"
        elif mom > 0.1: flow = "UP"
        
        # Result
        res = get_result(row)
        
        record = {
            "game_id": official_id if official_id else f"G_{d.replace('-','')}_{t[:3].upper()}",
            "date": d,
            "team": t,
            "matchup": f"{t} vs {row['opponent']}",
            "edge_score": edge,
            "fav_pct": prob,
            "flow_state": flow,
            "fatigue_state": "NORMAL", # Default
            "result": res,
            "has_semantic_data": (official_id in semantic_flags) if official_id else False,
            "story_headline": headline_map.get(official_id) if official_id else None,
            "story_body": body_map.get(official_id) if official_id else None, # Include Body
            "is_synthetic_id": not bool(official_id)
        }
        final_records.append(record)
        
    # Create DataFrame
    master_df = pd.DataFrame(final_records)
    master_df = master_df.sort_values('date')
    
    print(f"🎉 Master Index Build Complete: {len(master_df)} Games.")
    print(f"   - Semantic Coverage: {master_df['has_semantic_data'].sum()} Games.")
    
    # 4. Save
    output_path = "processed/master_chronicle_index.json"
    
    # Convert to list of dicts
    records = master_df.to_dict('records')
    
    with open(output_path, 'w') as f:
        json.dump(records, f, indent=2)
        
    print(f"💾 Saved to {output_path}")

if __name__ == "__main__":
    build_master_index()
