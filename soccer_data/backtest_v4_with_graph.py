import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os

class SoccerEngineV4WithGraph:
    def __init__(self, mapping_path, graph_insights_path):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)

        # Load graph intelligence
        with open(graph_insights_path, 'r') as f:
            insights = json.load(f)

            # Team regimes (xG over/under-performance)
            self.team_regimes = {}
            for team_data in insights.get('team_regimes', []):
                self.team_regimes[team_data['team']] = team_data['xg_diff']

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
        p_h = np.sum(np.tril(m, -1))
        p_d = np.sum(np.diag(m))
        p_a = np.sum(np.triu(m, 1))

        return p_h, p_d, p_a

    def apply_team_regime_adjustment(self, p_h, p_d, p_a, h_team, a_team):
        """
        Apply team performance regime adjustments
        Clinical teams (positive xG diff) win more often than xG suggests
        Wasteful teams (negative xG diff) win less often
        """
        h_regime = self.team_regimes.get(h_team, 0)
        a_regime = self.team_regimes.get(a_team, 0)

        # Adjustment scaling factor (empirical)
        # 0.15 xG diff = approx +3% win probability
        scaling = 0.20

        # Adjust home team
        if h_regime != 0:
            adjustment = h_regime * scaling
            p_h += adjustment
            # Reduce draw and away proportionally
            p_d -= adjustment * 0.5
            p_a -= adjustment * 0.5

        # Adjust away team
        if a_regime != 0:
            adjustment = a_regime * scaling
            p_a += adjustment
            # Reduce draw and home proportionally
            p_d -= adjustment * 0.5
            p_h -= adjustment * 0.5

        # Normalize to sum to 1.0
        total = p_h + p_d + p_a
        p_h /= total
        p_d /= total
        p_a /= total

        return p_h, p_d, p_a

def run_v4_with_graph_backtest():
    print("=" * 60)
    print("Soccer Engine V4 + Graph Intelligence")
    print("=" * 60)

    mapping_path = "processed/team_name_mapping.json"
    graph_path = "processed/graph_insights.json"

    engine = SoccerEngineV4WithGraph(mapping_path, graph_path)

    print(f"\n✅ Loaded {len(engine.team_regimes)} team regime adjustments")

    # Show top/bottom teams
    top_teams = sorted(engine.team_regimes.items(), key=lambda x: x[1], reverse=True)[:5]
    bottom_teams = sorted(engine.team_regimes.items(), key=lambda x: x[1])[:5]

    print("\n🔥 Top Clinical Teams (outperform xG):")
    for team, diff in top_teams:
        print(f"   {team:30s} +{diff:.3f} xG/game")

    print("\n⚠️  Bottom Wasteful Teams (underperform xG):")
    for team, diff in bottom_teams:
        print(f"   {team:30s} {diff:.3f} xG/game")

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
    adjustments_applied = 0

    print(f"\n🔄 Running backtest...")

    for idx, row in df.iterrows():
        h_exp = get_rolling(row['h_name'], row['datetime'])
        a_exp = get_rolling(row['a_name'], row['datetime'])
        if h_exp is None or a_exp is None: continue

        # Base probability calculation
        p_h, p_d, p_a = engine.calculate_probs(h_exp, a_exp)

        # Apply graph intelligence (team regime adjustment)
        p_h_adj, p_d_adj, p_a_adj = engine.apply_team_regime_adjustment(
            p_h, p_d, p_a,
            row['h_name'],
            row['a_name']
        )

        # Track adjustments
        if abs(p_h_adj - p_h) > 0.001:
            adjustments_applied += 1

        # Match Odds
        h_mapped = engine.mapping.get(row['h_name'])
        a_mapped = engine.mapping.get(row['a_name'])
        if not h_mapped or not a_mapped: continue

        m_odds = odds_df[(odds_df['HomeTeam'] == h_mapped) & (odds_df['AwayTeam'] == a_mapped)].head(1)
        if not m_odds.empty:
            o_h, o_d, o_a = m_odds['AvgH'].values[0], m_odds['AvgD'].values[0], m_odds['AvgA'].values[0]

            # Calculate edges
            edges = {'h': p_h_adj - (1/o_h), 'd': p_d_adj - (1/o_d), 'a': p_a_adj - (1/o_a)}

            # FIXED: Bet on highest probability (not highest edge)
            probs = {'h': p_h_adj, 'd': p_d_adj, 'a': p_a_adj}
            best = max(probs, key=probs.get)

            profit = 0
            if best == row['outcome']: profit = m_odds[f'Avg{best.upper()}'].values[0] - 1
            else: profit = -1

            results.append({
                "match": f"{row['h_name']} vs {row['a_name']}",
                "league": row['league'],
                "pred": best,
                "bet": best,
                "edge": edges[best],
                "actual": row['outcome'],
                "profit": profit,
                "p_h_base": p_h,
                "p_h_adj": p_h_adj,
                "adjustment": p_h_adj - p_h
            })

    output_df = pd.DataFrame(results)
    output_df.to_csv("processed/backtest_v4_with_graph.csv", index=False)

    print(f"\n" + "=" * 60)
    print("RESULTS - V4 + Graph Intelligence")
    print("=" * 60)

    print(f"\nSample Size: {len(output_df)}")
    print(f"Adjustments Applied: {adjustments_applied} matches ({adjustments_applied/len(output_df)*100:.1f}%)")
    print(f"\nPrediction Accuracy: {(output_df['pred'] == output_df['actual']).mean():.2%}")
    print(f"Betting Win Rate: {(output_df['profit'] > 0).mean():.2%}")
    print(f"Overall ROI: {output_df['profit'].mean():.2%}")

    # By league
    print(f"\n" + "-" * 60)
    print("By League:")
    print("-" * 60)
    for league in sorted(output_df['league'].unique()):
        league_df = output_df[output_df['league'] == league]
        roi = league_df['profit'].mean()
        acc = (league_df['pred'] == league_df['actual']).mean()
        print(f"  {league:15s} ROI: {roi:+6.2%}  Accuracy: {acc:.1%}  ({len(league_df)} bets)")

    print(f"\nOutput saved to: processed/backtest_v4_with_graph.csv")

    return output_df

if __name__ == "__main__":
    result_df = run_v4_with_graph_backtest()
