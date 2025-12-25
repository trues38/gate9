
import json
import math
import os

CACHE_DIR = "/Users/js/g9/nba_data/quant_engine_v1/quant_cache"

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def build_momentum(data_loader):
    print("Building Momentum Cache...")
    cache = {}
    
    # Iterate all teams in data_loader
    # data_loader.team_game_map keys are team_ids
    
    for tid_raw, history in data_loader.team_game_map.items():
        tid = str(tid_raw)
        
        # Recent 10 games
        l10 = history[:10]
        if not l10:
            cache[tid] = 0.5
            continue
            
        # Spec: NetRating = (PF - PA) / Games
        # Momentum = (NetRtg_Recent - NetRtg_Prev)
        # Normalized = sigmoid(momentum / 5)
        
        # Define Recent as L5, Prev as Next 5 (L6-10)
        recent = l10[:5]
        prev = l10[5:]
        
        if not recent:
            cache[tid] = 0.5
            continue
            
        # Recent NetRtg
        pf_r = sum(g['pts'] for g in recent)
        pa_r = sum(g['opp_pts'] for g in recent)
        nr_recent = (pf_r - pa_r) / len(recent)
        
        # Prev NetRtg
        if prev:
            pf_p = sum(g['pts'] for g in prev)
            pa_p = sum(g['opp_pts'] for g in prev)
            nr_prev = (pf_p - pa_p) / len(prev)
        else:
            nr_prev = 0 # No history, assume neutral baseline
            
        momentum_raw = nr_recent - nr_prev
        
        # Signmoid Normalization
        # e.g. Momentum +5 -> Sigmoid(1.0) ~= 0.73
        # Momentum +10 -> Sigmoid(2.0) ~= 0.88
        # Momentum 0 -> 0.5
        
        normalized = sigmoid(momentum_raw / 5)
        cache[tid] = round(normalized, 4)
        
    return cache

if __name__ == "__main__":
    # Test
    from data_loader import DataLoader
    dl = DataLoader()
    cache = build_momentum(dl)
    print(json.dumps(cache, indent=2))
