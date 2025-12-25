
import json

def build_pace(data_loader):
    print("Building Pace Cache...")
    cache = {}
    
    for tid_raw, history in data_loader.team_game_map.items():
        tid = str(tid_raw)
        
        l10 = history[:10]
        if not l10:
            cache[tid] = 98.0
            continue
            
        total_poss = 0
        total_games = 0
        
        for g in l10:
            # Formula: Pace = 0.5 * (TeamPoss + OppPoss)
            # Poss = FGA + 0.44*FTA + TOV - ORB
            # ORB Proxy: 0.25 * REB (Since ORB missing in raw logs)
            
            # Team Poss
            orb_est = 0.25 * g['reb']
            poss = g['fga'] + 0.44 * g['fta'] + g['tov'] - orb_est
            
            # Opp Poss
            opp_orb_est = 0.25 * g['opp_reb']
            opp_poss = g['opp_fga'] + 0.44 * g['opp_fta'] + g['opp_tov'] - opp_orb_est
            
            game_pace = 0.5 * (poss + opp_poss)
            total_poss += game_pace
            total_games += 1
            
        avg_pace = total_poss / total_games if total_games > 0 else 98.0
        cache[tid] = round(avg_pace, 2)
        
    return cache

if __name__ == "__main__":
    from data_loader import DataLoader
    dl = DataLoader()
    cache = build_pace(dl)
    print(json.dumps(cache, indent=2))
