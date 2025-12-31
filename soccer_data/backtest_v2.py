import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os

class SoccerEngineV2:
    def __init__(self, mapping_path):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)

    def calculate_dixon_coles_probs(self, h_exp, a_exp, rho=-0.1):
        """
        Calculates probabilities using Poisson with a Dixon-Coles adjustment for low-scoring draws.
        rho is the adjustment parameter (typically negative for soccer).
        """
        max_goals = 8
        h_probs = [poisson.pmf(i, h_exp) for i in range(max_goals)]
        a_probs = [poisson.pmf(i, a_exp) for i in range(max_goals)]
        
        m = np.outer(h_probs, a_probs)
        
        # Dixon-Coles Adjustment for (0,0), (1,0), (0,1), (1,1)
        # Simplified tau adjustment
        if h_exp > 0 and a_exp > 0:
            tau = {
                (0,0): 1 - (h_exp * a_exp * rho),
                (1,0): 1 + (a_exp * rho),
                (0,1): 1 + (h_exp * rho),
                (1,1): 1 - rho
            }
            for (i, j), val in tau.items():
                if i < max_goals and j < max_goals:
                    m[i, j] *= val

        # Normalize matrix
        m /= m.sum()
        
        # triu(m, 1) -> j > i (Away Goals > Home Goals) -> Away Win
        # tril(m, -1) -> i > j (Home Goals > Away Goals) -> Home Win
        p_h = np.sum(np.tril(m, -1))
        p_d = np.sum(np.diag(m))
        p_a = np.sum(np.triu(m, 1))
        
        return p_h, p_d, p_a

    def get_strict_mapping(self, name):
        return self.mapping.get(name)

def run_v2_backtest():
    print("--- Soccer Engine V2: Institutional Audit Fix ---")
    
    mapping_path = "soccer_data/processed/team_name_mapping.json"
    engine = SoccerEngineV2(mapping_path)
    
    # 1. Load Data
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
    df['h_name'] = df['h'].apply(lambda x: x['title'])
    df['a_name'] = df['a'].apply(lambda x: x['title'])
    df['h_xg'] = df['xG'].apply(lambda x: float(x['h']))
    df['a_xg'] = df['xG'].apply(lambda x: float(x['a']))
    df['h_goals'] = df['goals'].apply(lambda x: int(x['h']))
    df['a_goals'] = df['goals'].apply(lambda x: int(x['a']))
    df['outcome'] = df.apply(lambda x: 'h' if x['h_goals'] > x['a_goals'] else ('a' if x['a_goals'] > x['h_goals'] else 'd'), axis=1)

    # 2. Optimized Rolling Logic (Corrected per Auditor)
    def get_team_rolling_stats(team_name, current_date):
        # Extract both home and away appearances for the team
        mask = ((df['h_name'] == team_name) | (df['a_name'] == team_name)) & (df['datetime'] < current_date)
        team_history = df[mask].tail(10) # Last 10 games
        
        if len(team_history) < 5: return None
        
        # Extract xG for the team regardless of home/away
        team_xg = []
        for _, row in team_history.iterrows():
            if row['h_name'] == team_name: team_xg.append(row['h_xg'])
            else: team_xg.append(row['a_xg'])
            
        return np.mean(team_xg)

    # 3. Odds Matching (Strict Mapping)
    odds_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in odds_files])
    
    predictions = []
    for idx, row in df.iterrows():
        h_rolling = get_team_rolling_stats(row['h_name'], row['datetime'])
        a_rolling = get_team_rolling_stats(row['a_name'], row['datetime'])
        
        if h_rolling is None or a_rolling is None: continue
        
        # Calculate Probabilities with Dixon-Coles
        p_h, p_d, p_a = engine.calculate_dixon_coles_probs(h_rolling, a_rolling)
        
        # Strict Name Mapping
        o_h_name = engine.get_strict_mapping(row['h_name'])
        o_a_name = engine.get_strict_mapping(row['a_name'])
        
        if not o_h_name or not o_a_name: continue
        
        match_odds = odds_df[(odds_df['HomeTeam'] == o_h_name) & (odds_df['AwayTeam'] == o_a_name)].head(1)
        
        if not match_odds.empty:
            o_h, o_d, o_a = match_odds['AvgH'].values[0], match_odds['AvgD'].values[0], match_odds['AvgA'].values[0]
            
            # Prediction = Highest Probability
            probs = {'h': p_h, 'd': p_d, 'a': p_a}
            pred = max(probs, key=probs.get)
            
            # Edge Analysis
            edges = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}
            best_edge_type = max(edges, key=edges.get)
            
            predictions.append({
                "match": f"{row['h_name']} vs {row['a_name']}",
                "league": row['league'],
                "pred": pred,
                "best_edge": best_edge_type,
                "edge_val": edges[best_edge_type],
                "actual": row['outcome'],
                "o_h": o_h, "o_d": o_d, "o_a": o_a,
                "profit": (match_odds[f'Avg{best_edge_type.upper()}'].values[0] - 1) if best_edge_type == row['outcome'] else -1
            })

    results = pd.DataFrame(predictions)
    results.to_csv("soccer_data/processed/backtest_v2_results.csv", index=False)
    
    if results.empty:
        print("No predictions generated.")
        return

    # 4. Final Audit Verification Metrics
    accuracy = (results['pred'] == results['actual']).mean()
    win_rate = (results['best_edge'] == results['actual']).mean()
    
    print(f"\n--- V2 Final Verification ---")
    print(f"Total Predictive Matches: {len(results)}")
    print(f"Overall Prediction Accuracy: {accuracy:.2%} (vs Random 33.3%)")
    print(f"Edge-based Win Rate: {win_rate:.2%}")
    print(f"Overall ROI: {results['profit'].mean():.2%}")
    
    # Draw Accuracy Check
    draw_bets = results[results['best_edge'] == 'd']
    if not draw_bets.empty:
        draw_acc = (draw_bets['best_edge'] == draw_bets['actual']).mean()
        print(f"Draw Prediction Accuracy: {draw_acc:.2%} (Count: {len(draw_bets)})")

if __name__ == "__main__":
    run_v2_backtest()
