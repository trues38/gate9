import json
import os
import glob
from tqdm import tqdm
from datetime import datetime
import re

# Directories
DATA_DIR = "nba_data"
PLAYERS_FILE = os.path.join(DATA_DIR, "players", "top_250_active.json")
LEGACY_DIR = os.path.join(DATA_DIR, "legacy_raw")
MODERN_DIR = os.path.join(DATA_DIR, "stories_vector_tags_v2")
MODERN_RAW_DIR = os.path.join(DATA_DIR, "stories_raw")
OUTPUT_DIR = os.path.join(DATA_DIR, "players")

def load_players():
    if not os.path.exists(PLAYERS_FILE):
        print("❌ Top 250 Players file not found.")
        return []
    with open(PLAYERS_FILE, 'r') as f:
        return json.load(f)

def build_date_map():
    """Scans raw story files to map ID -> Date."""
    print("📅 Building Game Date Map...")
    date_map = {}
    
    # Modern Raw Scrape
    files = glob.glob(os.path.join(MODERN_RAW_DIR, "*.json"))
    for fpath in tqdm(files, desc="Scanning Modern Dates"):
        try:
            with open(fpath, 'r') as f:
                # Fast parse, maybe just grab first few chars? 
                # Better to load json safely.
                data = json.load(f)
                gid = data.get('game_id')
                # Date might be in 'date' or 'game_date' or in 'body' metadata
                # Usually standard ESPN scraper saves 'date' field if modified properly.
                # If not, try to extract from filename or body.
                # If file is named 'story_{id}.json', we need date inside.
                
                # Check known keys
                d = data.get('date') or data.get('game_date')
                if gid:
                    date_map[gid] = d
        except:
            pass
            
    # Legacy Raw Scrape (file name is legacy_{id}.json)
    # Inside, it has 'header': { 'competitions': [ { 'date': ... } ] }
    l_files = glob.glob(os.path.join(LEGACY_DIR, "*.json"))
    for fpath in tqdm(l_files, desc="Scanning Legacy Dates"):
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                # Structure: header -> competitions -> date
                # OR boxscore -> ...
                
                # ESPN Summary endpoint structure
                gid = os.path.basename(fpath).replace("legacy_", "").replace(".json", "")
                
                # Try header
                header = data.get('header', {})
                comps = header.get('competitions', [])
                if comps:
                    d = comps[0].get('date') # ISO string
                    if d:
                        date_map[gid] = d
        except:
            pass
            
    print(f"✅ Mapped {len(date_map)} game dates.")
    return date_map

def normalize_name(name):
    """Normalize for matching: 'LeBron James' -> 'lebronjames'"""
    return re.sub(r'[^a-z]', '', name.lower())

def compile_history():
    players = load_players()
    if not players: return
    
    # Index Players by Name for Tag Matching
    # Strict map: "LeBron James" -> ID
    # Loose map: "James" -> [ID1, ID2] (Ambiguous)
    
    player_map = {}
    name_lookup = {}
    
    for p in players:
        pid = p.get('id')
        name = p.get('name')
        
        if not pid or not name:
             continue
             
        # Initialize
        player_map[pid] = {
            "meta": p,
            "history": [] 
        }
        
        # Name Indexing
        norm = normalize_name(name)
        name_lookup[norm] = pid
        
        # Last name only (check collision)
        last = name.split()[-1]
        norm_last = normalize_name(last)
        # If collision, we mark as ambiguous? 
        # For MVP solution, we just overwrite (imperfect) or use list
        if norm_last not in name_lookup:
            name_lookup[norm_last] = pid
        else:
             # Collision! e.g. "Williams". 
             # Remove short version to be safe, require full name
             name_lookup[norm_last] = "AMBIGUOUS"

    date_map = build_date_map()
    
    # ---------------------------
    # 1. PROCESS LEGACY STATS
    # ---------------------------
    legacy_files = glob.glob(os.path.join(LEGACY_DIR, "*.json"))
    print(f"📚 Processing {len(legacy_files)} Legacy Games...")
    
    for fpath in tqdm(legacy_files):
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                
            gid = os.path.basename(fpath).replace("legacy_", "").replace(".json", "")
            date_str = date_map.get(gid, "Unknown")
            
            # Find stats for our players
            # ESPN Summary usually has 'boxscore' -> 'players' -> team -> statistics
            box = data.get('boxscore', {})
            teams = box.get('players', [])
            
            for team_entry in teams:
                stats_list = team_entry.get('statistics', [])
                for stat_entry in stats_list:
                    ath = stat_entry.get('athlete', {})
                    if not ath: continue
                    
                    # Match by ID first (Best)
                    pid = ath.get('id')
                    
                    # If ID matches our Top 250 list (Active players who played back then)
                    if pid in player_map:
                        # Add Event
                        player_map[pid]['history'].append({
                            "game_id": gid,
                            "date": date_str,
                            "type": "boxscore",
                            "stats": stat_entry.get('stats', []), # Raw array
                            "labels": stat_entry.get('labels', [])
                            # We can infer 'Health' from Minutes later
                        })
                    
        except Exception as e:
            pass

    # ---------------------------
    # 2. PROCESS MODERN VECTORS
    # ---------------------------
    vector_files = glob.glob(os.path.join(MODERN_DIR, "*.jsonl"))
    print(f"🧠 Processing {len(vector_files)} Modern Vector Files...")
    
    for fpath in tqdm(vector_files):
        gid = os.path.basename(fpath).replace(".jsonl", "")
        date_str = date_map.get(gid, "Unknown")
        
        try:
            with open(fpath, 'r') as f:
                for line in f:
                    chunk = json.loads(line)
                    tags = chunk.get("vector_tags", {})
                    
                    # Check PlayerFocus
                    focus_list = tags.get("PlayerFocus", [])
                    if not focus_list: continue
                    
                    # Match Names
                    for mentioned_name in focus_list:
                        norm = normalize_name(mentioned_name)
                        
                        target_id = name_lookup.get(norm)
                        
                        # Try split last name
                        if not target_id:
                            last = normalize_name(mentioned_name.split()[-1])
                            target_id = name_lookup.get(last)
                            
                        if target_id and target_id != "AMBIGUOUS":
                            # MATCH!
                            player_map[target_id]['history'].append({
                                "game_id": gid,
                                "date": date_str,
                                "type": "narrative_vector",
                                "vector_tags": tags,
                                "embedding": chunk.get("embedding", [])
                            })
                            
        except Exception as e:
            # print(f"Err {gid}: {e}")
            pass

    # ---------------------------
    # 3. SAVE RESULTS
    # ---------------------------
    print("💾 Saving Player Histories...")
    saved_count = 0
    for pid, p_data in player_map.items():
        hist = p_data['history']
        if hist:
            # Sort by date
            # Date format can be ISO strings or "YYYYMMDD"
            try:
                hist.sort(key=lambda x: x['date'] if x['date'] else "0000")
            except:
                pass # Best effort
                
            fname = os.path.join(OUTPUT_DIR, f"{pid}_history.json")
            with open(fname, 'w') as f:
                json.dump(p_data, f, indent=2)
            saved_count += 1
            
    print(f"✅ Compiled histories for {saved_count} / {len(players)} players.")

if __name__ == "__main__":
    compile_history()
