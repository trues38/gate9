
import os
import json
import glob
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict

INPUT_DIR = "nba_betting_report/input/"
OUTPUT_FILE = "nba_betting_report/backtest/pre_edge_results.jsonl"

class TeamHistory:
    def __init__(self):
        self.games = [] # list of dicts: {date, efg, reb, oreb_rate, poss, score, ...}
    
    def add_game(self, game_date, stats):
        self.games.append({
            "date": game_date,
            **stats
        })
        # Sort by date just in case
        self.games.sort(key=lambda x: x['date'])

    def get_last_n(self, n, strict_before_date):
        """Get last n games STRICTLY before strict_before_date"""
        valid_games = [g for g in self.games if g['date'] < strict_before_date]
        return valid_games[-n:]

def safe_mean(values):
    return np.mean(values) if values else 0.0

def safe_std(values):
    return np.std(values) if len(values) > 1 else 0.0

def normalize(val, min_v, max_v):
    """Normalize value to 0-100 scale based on expected range"""
    if val < min_v: val = min_v
    if val > max_v: val = max_v
    return ((val - min_v) / (max_v - min_v)) * 100

def calculate_features(home_hist, away_hist, game_date):
    """
    Calculate 4 distinct feature groups
    """
    # 1. Efficiency Trend (Home vs Away Gap)
    # We compare Home's trend vs Away's trend
    
    # Home Stats
    h_10 = home_hist.get_last_n(10, game_date)
    h_5 = home_hist.get_last_n(5, game_date)
    
    # Away Stats
    a_10 = away_hist.get_last_n(10, game_date)
    a_5 = away_hist.get_last_n(5, game_date)
    
    if not h_10 or not a_10:
        return None # Insufficient history
        
    # --- Feature 1: Efficiency Trend ---
    # Logic: Is the team improving?
    h_efg_10 = safe_mean([g['efg'] for g in h_10])
    h_efg_5 = safe_mean([g['efg'] for g in h_5])
    h_trend = h_efg_5 - h_efg_10
    
    a_efg_10 = safe_mean([g['efg'] for g in a_10])
    a_efg_5 = safe_mean([g['efg'] for g in a_5])
    a_trend = a_efg_5 - a_efg_10
    
    # The signal is the DIFFERENCE in trend (Home improvement vs Away improvement)
    # Plus, raw efficiency gap
    raw_eff_diff = h_efg_10 - a_efg_10
    trend_diff = h_trend - a_trend
    
    # Combined Efficiency Signal
    # We want 0-100.
    # Raw diff range: -0.10 to +0.10 approx
    # Trend diff range: -0.10 to +0.10 approx
    # Improve signal: (Raw + Trend)
    eff_val = (raw_eff_diff * 0.7) + (trend_diff * 0.3)
    # Norm: -0.15 to +0.15 -> 0-100
    eff_score = normalize(eff_val, -0.15, 0.15)
    
    # --- Feature 2: Rebounding Expectation ---
    # Home Reb vs Away Reb
    h_reb = safe_mean([g['reb'] for g in h_10])
    a_reb = safe_mean([g['reb'] for g in a_10])
    
    # OREB Rate is cleaner structural metric
    h_oreb_rate = safe_mean([g['oreb_rate'] for g in h_10])
    a_oreb_rate = safe_mean([g['oreb_rate'] for g in a_10])
    
    # Gap
    reb_gap = h_reb - a_reb
    oreb_gap = h_oreb_rate - a_oreb_rate
    
    # Combined Rebound Signal
    # Reb norm: -15 to +15
    # Oreb norm: -0.10 to +0.10
    reb_val = (reb_gap / 15.0) * 0.5 + (oreb_gap / 0.10) * 0.5
    # Map -1 to 1 -> 0 to 100
    reb_score = normalize(reb_val, -1.0, 1.0)
    
    
    # --- Feature 3: Pace Expectation ---
    # Not just speed, but control.
    h_poss = safe_mean([g['poss'] for g in h_10])
    a_poss = safe_mean([g['poss'] for g in a_10])
    
    # Pace match? Usually higher variance if paces strictly mismatch without control
    # Here we treat "Pace Advantage" as Home Ability to dictate? 
    # Or just simple Pace difference?
    # User Spec: "Pace Expectation: avg_poss, volatility".
    # Let's use simple Pace Deviation from League Avg (approx 100) or Deviation between teams?
    # Actually, structural edge often comes from Pace Mismatch + Efficiency.
    # Let's map "Pace Control" -> Lower volatility is better?
    h_vol = safe_mean([g['pace_vol'] for g in h_10]) # Oh wait, pace_vol is computed from history
    a_vol = safe_mean([g['pace_vol'] for g in a_10])
    
    # Let's compute volatility of the last 10 games directly
    h_pace_std = safe_std([g['poss'] for g in h_10])
    a_pace_std = safe_std([g['poss'] for g in a_10])
    
    # Signal: Lower volatility = Higher Structural Stability Score
    # But we want 'Edge'. 
    # Let's assume simpler: Just use Pace Diff as a proxy for "Clash" energy?
    # Actually user spec for Pre-Edge Score is sum of normalized features.
    # Let's assume input means "Quality of Pace" or "Stability of Pace".
    # Let's norm: Lower Std Dev -> Higher Score (More predictable)
    avg_std = (h_pace_std + a_pace_std) / 2
    # Norm 0 to 5. 0 is perfect (100), 5 is chaotic (0).
    pace_score = normalize(5 - avg_std, 0, 5)
    
    
    # --- Feature 4: Stability / Noise ---
    # Score Std Dev
    h_score_std = safe_std([g['score'] for g in h_10])
    a_score_std = safe_std([g['score'] for g in a_10])
    
    # Days Rest
    h_last = h_10[-1]['date']
    a_last = a_10[-1]['date']
    
    def days_diff(d1, d2):
        return (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d2, "%Y-%m-%d")).days
        
    h_rest = days_diff(game_date, h_last)
    a_rest = days_diff(game_date, a_last)
    
    # Rest Advantage (Home Rest - Away Rest)
    rest_diff = h_rest - a_rest
    # Stability: Lower Score Std is better
    std_avg = (h_score_std + a_score_std) / 2
    
    # Combined Stability
    # Std: 5 (Good) to 20 (Bad)
    # Rest: +2 (Good) to -2 (Bad)
    
    std_score = normalize(20 - std_avg, 0, 15) # High is stable
    rest_score = normalize(rest_diff, -3, 3) 
    
    stability_score = 0.7 * std_score + 0.3 * rest_score
    
    return {
        "efficiency": eff_score,
        "rebound": reb_score,
        "pace": pace_score,
        "stability": stability_score,
        "meta": {
            "h_rest": h_rest,
            "a_rest": a_rest
        }
    }

def calculate_pre_edge_score(features):
    # pre_edge_score = 0.30 * eff + 0.25 * reb + 0.20 * pace + 0.25 * stability
    score = (
        0.30 * features['efficiency'] +
        0.25 * features['rebound'] +
        0.20 * features['pace'] +
        0.25 * features['stability']
    )
    return round(score, 1)

def extract_game_stats(game, side):
    """
    Extract single game stats for history update
    """
    stats = game[f'{side}_stats']
    opp_stats = game['away_stats'] if side == 'home' else game['home_stats']
    
    # Basic Metrics
    fgm = float(stats['fieldGoalsMade'])
    fga = float(stats['fieldGoalsAttempted'])
    fg3m = float(stats['threePointFieldGoalsMade'])
    ftm = float(stats['freeThrowsMade'])
    fta = float(stats['freeThrowsAttempted'])
    oreb = float(stats['offensiveRebounds'])
    dreb = float(stats['defensiveRebounds'])
    all_reb = float(stats['totalRebounds'])
    tov = float(stats['totalTurnovers'])
    pts = float(stats['points'])
    
    opp_dreb = float(opp_stats['defensiveRebounds'])
    
    # Derived
    efg = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0
    poss = fga + tov + 0.44 * fta - oreb
    oreb_rate = oreb / (oreb + opp_dreb) if (oreb + opp_dreb) > 0 else 0
    
    return {
        "efg": efg,
        "reb": all_reb,
        "oreb_rate": oreb_rate,
        "poss": poss,
        "score": pts,
        "pace_vol": 0 # Individual game has no vol, calc on aggregate
    }

def main():
    if not os.path.exists("nba_betting_report/backtest"):
        os.makedirs("nba_betting_report/backtest")
        
    histories = defaultdict(TeamHistory)
    json_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    
    results = []
    
    print("🚀 Starting Pre-Game Engine Backtest Run...")
    
    for file_path in json_files:
        if "sample_input" in file_path: continue
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        daily_games = data.get("games", [])
        if not daily_games: continue
        
        current_date = daily_games[0]['date']
        print(f"  Processing Pre-Game for {current_date}...")
        
        # 1. Predict (Calculate Pre-Edge) using CURRENT history (Strictly D-1)
        for game in daily_games:
            home = game['teams']['home']
            away = game['teams']['away']
            game_id = game['game_id']
            
            # Calc Features
            feats = calculate_features(histories[home], histories[away], current_date)
            
            if feats:
                score = calculate_pre_edge_score(feats)
                results.append({
                    "date": current_date,
                    "game_id": game_id,
                    "pre_edge_score": score,
                    "features": feats
                })
            else:
                # First few games, no history
                pass
        
        # 2. Update History (feed today's games into history for tomorrow)
        for game in daily_games:
            home = game['teams']['home']
            away = game['teams']['away']
            
            # Add Home Game
            h_stats = extract_game_stats(game, 'home')
            histories[home].add_game(current_date, h_stats)
            
            # Add Away Game
            a_stats = extract_game_stats(game, 'away')
            histories[away].add_game(current_date, a_stats)

    # Save
    print(f"💾 Saving {len(results)} pre-game predictions to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        for res in results:
            f.write(json.dumps(res) + "\n")

if __name__ == "__main__":
    main()
