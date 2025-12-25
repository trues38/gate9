
import pandas as pd
import os
import json
from tqdm import tqdm

# Config
UPSETS_CSV = "/Users/js/g9/nba_data/quant_engine/historical_upset_candidates.csv"
STORIES_DIR = "/Users/js/g9/nba_data/stories_raw"
OUTPUT_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_raw.json"

def build_library():
    print("Loading upsets...")
    try:
        df = pd.read_csv(UPSETS_CSV, dtype={'game_id': str}) # Force string to keep structure if possible, though pandas might have already dropped leading 0s in previous save
    except FileNotFoundError:
        print("CSV not found. Please run scan_historical_upsets.py first.")
        return

    matched_count = 0
    missing_count = 0
    library_data = []

    print(f"Processing {len(df)} upsets...")

    for _, row in tqdm(df.iterrows(), total=len(df)):
        raw_id = row['game_id']
        # Pad ID to 10 digits
        game_id = raw_id.zfill(10) 
        
        # Expected filename
        filename = f"story_{game_id}.json"
        filepath = os.path.join(STORIES_DIR, filename)
        
        if os.path.exists(filepath):
            matched_count += 1
            with open(filepath, 'r') as f:
                story_data = json.load(f)
                
            # Combine Quant + Narrative
            entry = row.to_dict()
            entry['game_id'] = game_id # Use padded ID
            entry['story_headline'] = story_data.get('headline', '')
            entry['story_body'] = story_data.get('body', '')
            entry['story_date'] = story_data.get('date', '')
            
            library_data.append(entry)
        else:
            missing_count += 1
            # print(f"Missing story for {game_id} (Raw: {raw_id})")

    print(f"Matching Complete.")
    print(f"Matches Found: {matched_count}")
    print(f"Missing Stories: {missing_count}")
    
    match_rate = matched_count / len(df) if len(df) > 0 else 0
    print(f"Coverage: {match_rate:.1%}")

    if library_data:
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(library_data, f, indent=2)
        print(f"Saved {len(library_data)} records to {OUTPUT_JSON}")

if __name__ == "__main__":
    build_library()
