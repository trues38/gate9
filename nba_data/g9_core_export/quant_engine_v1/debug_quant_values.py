
import sys
import os
import json
sys.path.append("/Users/js/g9/nba_data/quant_engine_v1")
from data_loader import DataLoader
from build_momentum import build_momentum

def debug():
    print(">>> DEBUG QUANT VALUES <<<")
    
    # 1. Load Data
    loader = DataLoader() # DataLoader logic will run here
    print(f"Team Histories: {len(loader.team_game_map)} teams loaded.")
    
    # 2. Pick a Team (e.g., GSW - 1610612744)
    # Check if key exists as int or str
    tid = 1610612744
    if tid not in loader.team_game_map:
        print(f"GSW ({tid}) not found in map keys: {list(loader.team_game_map.keys())[:5]}")
        return

    hist = loader.team_game_map[tid]
    print(f"GSW History Length: {len(hist)}")
    if hist:
        print("Latest Game:", hist[0])
        print("Oldest Game:", hist[-1])
        
    # 3. Test Momentum Build
    print("\n--- Testing Momentum Calculation ---")
    mom_val = build_momentum(loader)
    # build_momentum returns full dict.
    # We want to see the LOGIC for one team.
    # Refactoring verify logic:
    
    # Logic from build_momentum.py (approx)
    # recent = hist[:5]
    # prev = hist[5:10]
    # net_rtg = (pts - opp_pts)
    
    recent = hist[:5]
    prev = hist[5:10]
    
    def calc_net_rtg(games):
        if not games: return 0.0
        diff_sum = sum([g['margin'] for g in games])
        return diff_sum / len(games)
        
    rec_val = calc_net_rtg(recent)
    prev_val = calc_net_rtg(prev)
    print(f"Recent NetRtg (L5): {rec_val}")
    print(f"Prev NetRtg (L5-10): {prev_val}")
    
    diff = rec_val - prev_val
    print(f"Momentum Diff: {diff}")
    
    # Sigmoid
    import math
    def sigmoid(x):
        return 1 / (1 + math.exp(-x))
        
    # In builder: sigmoid(diff / 5)
    final = sigmoid(diff / 5.0)
    print(f"Calculated Momentum: {final}")
    
    # 4. Check Defense
    print("\n--- Testing Defense Calculation ---")
    # Logic: normalize(opp_pts)
    # avg_opp = sum(opp_pts) / len
    opp_pts = [g['opp_pts'] for g in hist]
    avg_def = sum(opp_pts) / len(opp_pts) if opp_pts else 0
    print(f"Avg Opp Pts: {avg_def}")

if __name__ == "__main__":
    debug()
