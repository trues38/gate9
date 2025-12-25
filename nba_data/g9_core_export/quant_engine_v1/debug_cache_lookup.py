
import sys
import json
import os

sys.path.append("/Users/js/g9/nba_data/quant_engine_v1")
from cache_engine import CacheFusionEngine

def debug():
    print(">>> DEBUG CACHE LOOKUP <<<")
    engine = CacheFusionEngine()
    
    # 1. Check Cache Keys
    pace_keys = list(engine.cache['pace'].keys())
    print(f"Pace Cache Size: {len(pace_keys)}")
    print(f"Sample Pace Keys: {pace_keys[:5]}")
    
    # 2. Load Schedule to get a Target ID
    with open("/Users/js/g9/nba_data/schedule_2025.json", 'r') as f:
        schedule = json.load(f)
        
    # Find a game for 2025-12-12
    target_date = "2025-12-12"
    target_game = None
    for s in schedule:
        if target_date in s['date']: # Approximate match
             target_game = s
             break
    
    # If standard iso date check failed, try specific logic
    if not target_game:
        # Just grab the first game
        target_game = schedule[0]
        print("Using First Game in Schedule as Test Case")
        
    print(f"Test Game: {target_game['home_team']} (ID: {target_game['home_id']}) vs {target_game['away_team']} (ID: {target_game['away_id']})")
    
    hid = target_game['home_id']
    aid = target_game['away_id']
    
    # 3. Perform Lookup
    print(f"Looking up Home ID: {hid} (Type: {type(hid)})")
    h_metrics = engine.get_quant_metrics(hid)
    print("Home Metrics:", h_metrics)
    
    print(f"Looking up Away ID: {aid} (Type: {type(aid)})")
    a_metrics = engine.get_quant_metrics(aid)
    print("Away Metrics:", a_metrics)
    
    # 4. Direct Cache Check
    str_hid = str(hid)
    print(f"Direct Pace Check ['{str_hid}']: {engine.cache['pace'].get(str_hid)}")

if __name__ == "__main__":
    debug()
