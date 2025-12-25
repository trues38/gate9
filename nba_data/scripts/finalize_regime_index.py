
import json
import os

INPUT_FILE = "processed/master_regime_index.jsonl"
OUTPUT_FILE = "processed/nba_regime_index_v1.json"

def clean_and_sort():
    print(f"🧹 Cleaning {INPUT_FILE}...")
    
    data = []
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            try:
                row = json.loads(line)
                
                # 1. Clean ID
                clean_id = row['game_id']
                if clean_id.startswith("G_"):
                    clean_id = clean_id[2:] # Remove G_
                
                # 2. Select & Order Columns
                new_row = {
                    "id": clean_id,
                    "date": row['date'],
                    "team": row['team'],
                    "matchup": row['matchup'],
                    "regime_type": row.get('regime_type', 'Unknown'),
                    "regime_delta": row.get('narrative_delta'), # Rename for clarity?
                    "headline": row.get('headline'),
                    "edge_score": row.get('edge_score'),
                    "fav_pct": row.get('fav_pct'),
                    "flow_state": row.get('flow_state'),
                    "result": row.get('result')
                }
                
                data.append(new_row)
            except: pass
            
    # 3. Sort by Date
    print("Sorting by Date...")
    data.sort(key=lambda x: x['date'])
    
    # 4. Save
    print(f"💾 Saving {len(data)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
        
    print("✅ Done.")

if __name__ == "__main__":
    clean_and_sort()
