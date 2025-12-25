import json
from datetime import datetime

def build_rest_days(data_loader):
    print("Building Rest Days Cache...")
    cache = {}
    
    # We need to know "Target Date" for Rest Calculation, but Cache is generic?
    # Actually, Rest is dynamic relative to "Next Game".
    # But for "Cache", maybe we store "Date of Last Game".
    # And the Engine calculates Rest.
    
    # "New Quant Core Metrics" -> REST_DAYS.
    # Required Inputs: Schedule Data.
    # The Cache file should probably store: { tid: "YYYY-MM-DD" (Last Game) }
    # Then `cache_engine` computes Rest based on Target Date.
    
    # Logic:
    # 1. Inspect History[0].date
    
    for tid_raw, history in data_loader.team_game_map.items():
        tid = str(tid_raw)
        if not history:
            cache[tid] = "1900-01-01"
            continue
            
        last_date = history[0]['date']
        cache[tid] = last_date
        
    return cache

if __name__ == "__main__":
    from data_loader import DataLoader
    dl = DataLoader()
    cache = build_rest_days(dl)
    print(json.dumps(cache, indent=2))
