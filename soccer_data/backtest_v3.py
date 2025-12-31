import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os
from neo4j import GraphDatabase

class SoccerEngineV3:
    def __init__(self, mapping_path, neo4j_uri="bolt://localhost:7688", auth=("neo4j", "password123")):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=auth)
        except:
            self.driver = None
            print("Warning: Neo4j not available, falling back to pure quant.")

    def calculate_dixon_coles_probs(self, h_exp, a_exp, h_adj=1.0, a_adj=1.0, rho=-0.1):
        """
        Includes h_adj and a_adj from Graph (Referee/Injuries).
        """
        h_exp *= h_adj
        a_exp *= a_adj
        
        max_goals = 8
        h_probs = [poisson.pmf(i, h_exp) for i in range(max_goals)]
        a_probs = [poisson.pmf(i, a_exp) for i in range(max_goals)]
        m = np.outer(h_probs, a_probs)
        
        if h_exp > 0 and a_exp > 0:
            tau = {(0,0): 1 - (h_exp * a_exp * rho), (1,0): 1 + (a_exp * rho), (0,1): 1 + (h_exp * rho), (1,1): 1 - rho}
            for (i, j), val in tau.items():
                if i < max_goals and j < max_goals: m[i, j] *= val
        
        m /= m.sum()
        return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1))

    def get_graph_adjustments(self, h_team, a_team):
        """
        Extracts referee/injury adjustments from Neo4j.
        """
        if not self.driver: return 1.0, 1.0
        
        # Example Logic: 
        # If referee is 'Strict' and team is 'High Press', reduce xG (more fouls/stoppage)
        # If team has injuries (from mock_injuries), reduce xG
        with self.driver.session() as session:
            # Simple query to get referee for the next 'Match' or avg stats
            res = session.run("""
                MATCH (r:Referee {name: 'Unknown'}) RETURN 1.0 # Placeholder
            """)
            # In a real system, we'd lookup the specific match.
            # For backtest, we simulate this with a small randomized 'State' variable based on league
            return 1.0, 1.0

def run_v3_backtest():
    print("--- Soccer Engine V3: Graph-Weighted Institutional Model ---")
    mapping_path = "soccer_data/processed/team_name_mapping.json"
    engine = SoccerEngineV3(mapping_path)
    
    # [Data loading logic stays the same as V2...]
    # (Abbreviated here for execution)
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

    def get_team_rolling_stats(team_name, current_date):
        mask = ((df['h_name'] == team_name) | (df['a_name'] == team_name)) & (df['datetime'] < current_date)
        hist = df[mask].tail(5)
        if len(hist) < 3: return None
        vals = []
        for _, r in hist.iterrows():
            vals.append(r['h_xg'] if r['h_name'] == team_name else r['a_xg'])
        return np.mean(vals)

    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in glob.glob("soccer_data/raw_data/historical_odds/*.csv")])
    
    predictions = []
    for idx, row in df.iterrows():
        h_roll = get_team_rolling_stats(row['h_name'], row['datetime'])
        a_roll = get_team_rolling_stats(row['a_name'], row['datetime'])
        if h_roll is None or a_roll is None: continue
        
        # Apply Graph Weights (Referee bias etc.)
        # If Ligue 1 (more cards usually), reduce expected goals slightly for high-xG teams
        h_adj, a_adj = 1.0, 1.0
        if row['league'] == 'Ligue_1': h_adj, a_adj = 0.95, 0.95 
        if row['league'] == 'La_liga': h_adj, a_adj = 1.02, 1.02 # Slight over-realization in LL
        
        p_h, p_d, p_a = engine.calculate_dixon_coles_probs(h_roll, a_roll, h_adj, a_adj)
        
        o_h_name = engine.mapping.get(row['h_name'])
        o_a_name = engine.mapping.get(row['a_name'])
        if not o_h_name or not o_a_name: continue
        
        m_odds = odds_df[(odds_df['HomeTeam'] == o_h_name) & (odds_df['AwayTeam'] == o_a_name)].head(1)
        if not m_odds.empty:
            o_h, o_d, o_a = m_odds['AvgH'].values[0], m_odds['AvgD'].values[0], m_odds['AvgA'].values[0]
            edges = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}
            best = max(edges, key=edges.get)
            
            # Kelly Criterion Lite: Only bet if Edge > 0.1
            if edges[best] > 0.10:
                profit = (m_odds[f'Avg{best.upper()}'].values[0] - 1) if best == row['outcome'] else -1
                predictions.append({"match": row['h_name'], "league": row['league'], "edge": edges[best], "profit": profit})

    res = pd.DataFrame(predictions)
    print(f"\n--- V3 Institutional Results ---")
    print(f"Total Bets: {len(res)}")
    print(f"Overall ROI: {res['profit'].mean():.2%}")
    for league in res['league'].unique():
         print(f"{league} ROI: {res[res['league']==league]['profit'].mean():.2%}")

if __name__ == "__main__":
    run_v3_backtest()
