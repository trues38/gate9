import pandas as pd
import numpy as np
import json
import glob
import os
from scipy.stats import poisson

def calculate_probabilities(h_xg, a_xg):
    """
    State-of-the-art Poisson calculation for Soccer Win/Draw/Loss probabilities.
    """
    # Create goal distribution matrix (up to 10 goals)
    max_goals = 10
    h_probs = [poisson.pmf(i, h_xg) for i in range(max_goals)]
    a_probs = [poisson.pmf(i, a_xg) for i in range(max_goals)]
    
    m = np.outer(h_probs, a_probs)
    
    p_h = np.sum(np.triu(m, 1).T) # Home Win
    p_d = np.sum(np.diag(m))      # Draw
    p_a = np.sum(np.tril(m, -1).T) # Away Win
    
    return p_h, p_d, p_a

def run_advanced_backtest():
    print("Initializing Multi-Season High-Fidelity Backtest...")
    
    # 1. Load All Games (2023 + 2024 if exist)
    results_files = glob.glob("soccer_data/raw_data/understat/*/202*/results.json")
    odds_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    
    # Load odds
    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in odds_files])
    
    records = []
    for rf in results_files:
        with open(rf, 'r') as f:
            matches = json.load(f)
        
        for m in matches:
            h_team, a_team = m['h']['title'], m['a']['title']
            h_xg, a_xg = float(m['xG']['h']), float(m['xG']['a'])
            
            # Poisson probabilities
            p_h, p_d, p_a = calculate_probabilities(h_xg, a_xg)
            
            # Match with odds
            match_odds = odds_df[
                (odds_df['HomeTeam'].str.contains(h_team[:5])) & 
                (odds_df['AwayTeam'].str.contains(a_team[:5]))
            ].head(1)
            
            if not match_odds.empty:
                odd_h = match_odds['AvgH'].values[0]
                odd_d = match_odds['AvgD'].values[0]
                odd_a = match_odds['AvgA'].values[0]
                
                # Market Probabilities
                m_p_h, m_p_d, m_p_a = 1/odd_h, 1/odd_d, 1/odd_a
                
                # Check outcome
                h_goals, a_goals = int(m['goals']['h']), int(m['goals']['a'])
                actual = 'h' if h_goals > a_goals else ('a' if a_goals > h_goals else 'd')
                
                records.append({
                    "match": f"{h_team} vs {a_team}",
                    "h_xg": h_xg, "a_xg": a_xg,
                    "p_h": p_h, "p_d": p_d, "p_a": p_a,
                    "odd_h": odd_h, "odd_d": odd_d, "odd_a": odd_a,
                    "edge_h": p_h - m_p_h,
                    "outcome": actual,
                    "profit_h": (odd_h - 1) if actual == 'h' else -1
                })

    df = pd.DataFrame(records)
    df.to_csv("soccer_data/processed/high_fidelity_backtest.csv", index=False)
    
    # Analyze Strategy: Bet on H if edge_h > 0.05
    strategy = df[df['edge_h'] > 0.05]
    roi = strategy['profit_h'].mean()
    win_rate = (strategy['outcome'] == 'h').mean()
    
    print(f"\n--- Backtest Results (Sample Size: {len(df)}) ---")
    print(f"Strategy: High Edge Home Bets (>5%)")
    print(f"Sample Size: {len(strategy)}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Projected ROI: {roi:.2%}")

if __name__ == "__main__":
    run_advanced_backtest()
