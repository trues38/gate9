import json
import os
import glob
import numpy as np
from datetime import datetime
from tqdm import tqdm
import re

# Configuration
VECTOR_DIR = "nba_data/stories_vector_tags_v2"
RAW_STORY_DIR = "nba_data/stories_raw"
OUTPUT_DIR = "nba_data/persona_vectors"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def normalize_name(name):
    # "LeBron James" -> "lebron_james"
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

def load_date_map():
    """
    Builds a map of game_id -> date from raw stories.
    This is faster than opening every raw file during the loop.
    """
    print("📅 Building Game Date Map...")
    date_map = {}
    raw_files = glob.glob(os.path.join(RAW_STORY_DIR, "*.json"))
    for fpath in tqdm(raw_files):
        try:
            with open(fpath, 'r') as f:
                d = json.load(f)
                gid = d.get('game_id') or d.get('espn_id')
                # Date format in raw is usually "YYYYMMDD" or "YYYY-MM-DD"
                # Let's standardize to string YYYY-MM-DD
                dt = d.get('date')
                if gid and dt:
                    date_map[str(gid)] = dt
        except:
            pass
    return date_map

def build_personas():
    date_map = load_date_map()
    
    files = glob.glob(os.path.join(VECTOR_DIR, "*.jsonl"))
    print(f"🧠 Processing {len(files)} vector files for Personas...")
    
    # Structure: personas[name] = [ {date, vector, specific_tags}, ... ]
    personas = {}
    
    for fpath in tqdm(files):
        try:
            with open(fpath, 'r') as f:
                # JSONL but distinct files per game usually have 1 line
                for line in f:
                    data = json.loads(line)
                    game_id = str(data['game_id'])
                    vector = data['embedding']
                    tags = data.get('vector_tags', {})
                    
                    # Get Date
                    game_date = date_map.get(game_id, "1900-01-01")
                    
                    # Players
                    players = tags.get('PlayerFocus', [])
                    
                    # Sentiment Context
                    context = {
                        "game_id": game_id,
                        "date": game_date,
                        "intensity": tags.get('NarrativeIntensity'),
                        "tone": tags.get('EmotionalTone'),
                        "vector": vector
                    }
                    
                    for p in players:
                        if p not in personas:
                            personas[p] = []
                        personas[p].append(context)
                        
        except Exception as e:
            # print(f"Error {fpath}: {e}")
            pass

    print(f"👥 Found {len(personas)} unique personas. Aggregating...")
    
    # Aggregation & Output
    count_saved = 0
    for name, history in tqdm(personas.items()):
        if len(history) < 3: continue # Skip if minimal history
        
        # Sort by date (Handle mixed formats)
        def parse_date(d_str):
            try:
                return datetime.strptime(d_str, "%Y-%m-%d")
            except:
                try:
                    return datetime.strptime(d_str, "%b %d, %Y")
                except:
                    return datetime(1900, 1, 1)

        history.sort(key=lambda x: parse_date(x['date']))
        
        # Calculate Weighted Average (Decay)
        # Weights: recent is more important. 
        # Simple linear weight: index+1
        vectors = np.array([h['vector'] for h in history])
        weights = np.arange(1, len(vectors) + 1)
        
        weighted_avg = np.average(vectors, axis=0, weights=weights)
        
        # Volatility: Std Dev of vectors
        volatility = np.mean(np.std(vectors, axis=0)) 
        
        # Recent Tone (Last 5 games)
        recent_tones = [h['tone'] for h in history[-5:]]
        
        result = {
            "name": name,
            "total_games": len(history),
            "last_active": history[-1]['date'],
            "persona_vector": weighted_avg.tolist(),
            "volatility_index": float(volatility),
            "recent_tones": recent_tones,
            "history_summary": [
                {"date": h['date'], "tone": h['tone'], "intensity": h['intensity']} 
                for h in history
            ]
        }
        
        fname = normalize_name(name) + ".json"
        with open(os.path.join(OUTPUT_DIR, fname), 'w') as out:
            json.dump(result, out, indent=2)
            
        count_saved += 1
        
    print(f"✅ Generated {count_saved} Persona Vectors in {OUTPUT_DIR}")

if __name__ == "__main__":
    build_personas()
