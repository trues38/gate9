import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os

class SoccerEngineV4:
    def __init__(self, mapping_path):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)

    def calculate_probs(self, h_exp, a_exp, rho=-0.1):
        """
        Dixon-Coles adjusted Poisson.
        i = Home Goals, j = Away Goals
        """
        max_goals = 10
        h_probs = [poisson.pmf(i, h_exp) for i in range(max_goals)]
        a_probs = [poisson.pmf(i, a_exp) for i in range(max_goals)]
        m = np.outer(h_probs, a_probs)
        
        # Tau adjustment for low scores
        if h_exp > 0 and a_exp > 0:
            tau = {(0,0): 1 - (h_exp * a_exp * rho), (1,0): 1 + (a_exp * rho), (0,1): 1 + (h_exp * rho), (1,1): 1 - rho}
            for (i, j), val in tau.items():
                if i < max_goals and j < max_goals: m[i, j] *= val
        
        m /= m.sum()
        
        # PROBABILITY MATH (VERIFIED BY UNIT TEST)
        # tril(m, -1) -> i > j -> Home Win
        # diag(m)     -> i = j -> Draw
        # triu(m, 1)  -> j > i -> Away Win
        p_h = np.sum(np.tril(m, -1))
        p_d = np.sum(np.diag(m))
        p_a = np.sum(np.triu(m, 1))
        
        return p_h, p_d, p_a

def run_v4_backtest():
    print("--- [AUDIT-PROOF] Soccer Engine V4 ---")
    mapping_path = "processed/team_name_mapping.json"
    engine = SoccerEngineV4(mapping_path)

    # 1. Load Match Data
    results_files = glob.glob("raw_data/understat/*/202*/results.json")
    all_matches = []
    for rf in results_files:
        with open(rf, 'r') as f:
            league = rf.split('/')[-3]
            for m in json.load(f):
                m['league'] = league
                all_matches.append(m)
    
    df = pd.DataFrame(all_matches)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')
    df['h_name'] = df['h'].apply(lambda x: x['title'])
    df['a_name'] = df['a'].apply(lambda x: x['title'])
    df['h_xg'] = df['xG'].apply(lambda x: float(x['h']))
    df['a_xg'] = df['xG'].apply(lambda x: float(x['a']))
    df['outcome'] = df.apply(lambda x: 'h' if int(x['goals']['h']) > int(x['goals']['a']) else ('a' if int(x['goals']['a']) > int(x['goals']['h']) else 'd'), axis=1)

    # 2. Predictive Rolling (Strict 5 games)
    def get_rolling(team, date):
        mask = ((df['h_name'] == team) | (df['a_name'] == team)) & (df['datetime'] < date)
        hist = df[mask].tail(5)
        if len(hist) < 3: return None
        return np.mean([r['h_xg'] if r['h_name'] == team else r['a_xg'] for _, r in hist.iterrows()])

    # 3. Market Data
    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in glob.glob("raw_data/historical_odds/*.csv")])
    
    results = []
    for idx, row in df.iterrows():
        h_exp = get_rolling(row['h_name'], row['datetime'])
        a_exp = get_rolling(row['a_name'], row['datetime'])
        if h_exp is None or a_exp is None: continue
        
        p_h, p_d, p_a = engine.calculate_probs(h_exp, a_exp)
        
        # Match Odds
        h_mapped = engine.mapping.get(row['h_name'])
        a_mapped = engine.mapping.get(row['a_name'])
        if not h_mapped or not a_mapped: continue
        
        m_odds = odds_df[(odds_df['HomeTeam'] == h_mapped) & (odds_df['AwayTeam'] == a_mapped)].head(1)
        if not m_odds.empty:
            o_h, o_d, o_a = m_odds['AvgH'].values[0], m_odds['AvgD'].values[0], m_odds['AvgA'].values[0]

            # Calculate edges for analysis
            edges = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}

            # FIXED: Bet on highest probability (not highest edge)
            probs = {'h': p_h, 'd': p_d, 'a': p_a}
            best = max(probs, key=probs.get)

            profit = 0
            if best == row['outcome']: profit = m_odds[f'Avg{best.upper()}'].values[0] - 1
            else: profit = -1
            
            results.append({
                "match": f"{row['h_name']} vs {row['a_name']}",
                "league": row['league'],
                "pred": max({'h':p_h, 'd':p_d, 'a':p_a}, key={'h':p_h, 'd':p_d, 'a':p_a}.get),
                "bet": best,
                "edge": edges[best],
                "actual": row['outcome'],
                "profit": profit
            })

    output_df = pd.DataFrame(results)
    output_df.to_csv("processed/backtest_v4_baseline.csv", index=False)

    print(f"\nBacktest Complete. Sample Size: {len(output_df)}")
    print(f"Prediction Accuracy: {(output_df['pred'] == output_df['actual']).mean():.2%}")
    print(f"Betting Win Rate: {(output_df['profit'] > 0).mean():.2%}")
    print(f"Overall ROI: {output_df['profit'].mean():.2%}")

    # By league
    print(f"\nBy League:")
    for league in sorted(output_df['league'].unique()):
        league_df = output_df[output_df['league'] == league]
        roi = league_df['profit'].mean()
        acc = (league_df['pred'] == league_df['actual']).mean()
        print(f"  {league:15s} ROI: {roi:+6.2%}  Accuracy: {acc:.1%}  ({len(league_df)} bets)")

    print(f"\nOutput saved to: processed/backtest_v4_baseline.csv")

if __name__ == "__main__":
    run_v4_backtest()
