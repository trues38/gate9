import os
import json
from data_loader import DataLoader
from build_pace import build_pace
from build_net_rating import build_net_rating
from build_volatility import build_volatility
from build_rest_days import build_rest_days

CACHE_DIR = "/Users/js/g9/nba_data/quant_engine_v1/quant_cache"

def save_json(name, data):
    path = os.path.join(CACHE_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {name}")

def rebuild():
    print(">>> STARTING QUANT ENGINE REBUILD (V1.0) <<<")
    dl = DataLoader()
    
    # 1. Net Rating (L10)
    net_rtg = build_net_rating(dl)
    save_json("net_rating.json", net_rtg)
    
    # 2. Pace (L10)
    pace = build_pace(dl)
    save_json("pace.json", pace)
    
    # 3. Rest Days (Last Game Date)
    rest = build_rest_days(dl)
    save_json("rest_days.json", rest)
    
    # 4. Volatility (L10)
    vol = build_volatility(dl)
    save_json("volatility.json", vol)
    
    print(">>> CACHE REBUILD COMPLETE (V-REPAIRED) <<<")

if __name__ == "__main__":
    rebuild()
