import pandas as pd
import numpy as np
import json
import glob
import os
from scipy.stats import poisson

def calculate_probabilities(h_xg, a_xg):
    max_goals = 10
    h_probs = [poisson.pmf(i, h_xg) for i in range(max_goals)]
    a_probs = [poisson.pmf(i, a_xg) for i in range(max_goals)]
    m = np.outer(h_probs, a_probs)
    return np.sum(np.triu(m, 1).T), np.sum(np.diag(m)), np.sum(np.tril(m, -1).T)

def run_predictive_backtest():
    print("--- Running Stress Test: Rolling xG Predictive Model ---")
    print("Goal: Eliminate Hindsight Bias (Using only pre-match data)")
    
    # 1. Load All Games
    results_files = glob.glob("soccer_data/raw_data/understat/*/202*/results.json")
    all_matches = []
    for rf in results_files:
        with open(rf, 'r') as f:
            league = rf.split('/')[-3]
            m_list = json.load(f)
            for m in m_list:
                m['league'] = league
                all_matches.append(m)
    
    df = pd.DataFrame(all_matches)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')
    
    # Extract titles and xG
    df['h_name'] = df['h'].apply(lambda x: x['title'])
    df['a_name'] = df['a'].apply(lambda x: x['title'])
    df['h_xg_val'] = df['xG'].apply(lambda x: float(x['h']))
    df['a_xg_val'] = df['xG'].apply(lambda x: float(x['a']))
    df['h_goals'] = df['goals'].apply(lambda x: int(x['h']))
    df['a_goals'] = df['goals'].apply(lambda x: int(x['a']))
    df['outcome'] = df.apply(lambda x: 'h' if x['h_goals'] > x['a_goals'] else ('a' if x['a_goals'] > x['h_goals'] else 'd'), axis=1)

    # 2. Calculate Rolling xG (Last 5 Games) for each team
    # This is the 'Predictive' part.
    def get_rolling_xg(row, team_name, current_date):
        # Home games for this team
        h_games = df[(df['h_name'] == team_name) & (df['datetime'] < current_date)].tail(5)
        # Away games for this team
        a_games = df[(df['a_name'] == team_name) & (df['datetime'] < current_date)].tail(5)
        
        recent_xg = pd.concat([h_games['h_xg_val'], a_games['a_xg_val']])
        if len(recent_xg) < 3: return None # Need at least 3 games of history
        return recent_xg.mean()

    # 3. Simulate Betting
    odds_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in odds_files])
    
    predictions = []
    for idx, row in df.iterrows():
        # Get PRE-MATCH expected xG
        h_exp_xg = get_rolling_xg(row, row['h_name'], row['datetime'])
        a_exp_xg = get_rolling_xg(row, row['a_name'], row['datetime'])
        
        if h_exp_xg is None or a_exp_xg is None: continue
        
        # Calculate Pred Probabilities
        p_h, p_d, p_a = calculate_probabilities(h_exp_xg, a_exp_xg)
        
        # Match with Odds
        match_odds = odds_df[
            (odds_df['HomeTeam'].str.contains(row['h_name'][:5])) & 
            (odds_df['AwayTeam'].str.contains(row['a_name'][:5]))
        ].head(1)
        
        if not match_odds.empty:
            o_h, o_d, o_a = match_odds['AvgH'].values[0], match_odds['AvgD'].values[0], match_odds['AvgA'].values[0]
            
            # Find Best Edge
            edges = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}
            best = max(edges, key=edges.get)
            
            if edges[best] > 0.05: # Minimal Edge Threshold
                if best == 'h': profit = (o_h - 1) if row['outcome'] == 'h' else -1
                elif best == 'd': profit = (o_d - 1) if row['outcome'] == 'd' else -1
                else: profit = (o_a - 1) if row['outcome'] == 'a' else -1
                
                predictions.append({
                    "match": f"{row['h_name']} vs {row['a_name']}",
                    "edge": edges[best],
                    "best_type": best,
                    "profit": profit
                })

    pred_df = pd.DataFrame(predictions)
    if not pred_df.empty:
        print(f"\n--- REALISTIC PREDICTIVE RESULTS (Rolling Window) ---")
        print(f"Total Bets Placed: {len(pred_df)}")
        print(f"Realistic ROI: {pred_df['profit'].mean():.2%}")
        print(f"Cumulative Profit (1unit/bet): {pred_df['profit'].sum():.2f}")
    else:
        print("No high-edge games found with rolling window.")

if __name__ == "__main__":
    run_predictive_backtest()
