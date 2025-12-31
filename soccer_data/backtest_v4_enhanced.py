import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os

class SoccerEngineV4Enhanced:
    def __init__(self, mapping_path, graph_insights_path):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)

        # Load graph-based intelligence
        with open(graph_insights_path, 'r') as f:
            insights = json.load(f)
            self.referee_impact = {r['referee']: r['home_xg_diff'] for r in insights['referee_impact']}
            self.team_regimes = {r['team']: r['xg_diff'] for r in insights['team_regimes']}
            self.graph_edges = insights['graph_edges']

        # Create referee-team interaction lookup
        self.interactions = {}
        for edge in self.graph_edges:
            key = (edge['team'], edge['referee'])
            self.interactions[key] = edge['impact']

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

    def apply_graph_intelligence(self, p_h, p_d, p_a, h_name, a_name, referee=None):
        """
        Apply graph-based adjustments to base probabilities.

        Enhancements:
        1. Referee impact on home advantage
        2. Team regime classification (clinical finishers vs wasteful)
        3. Referee-team interaction effects
        """
        original_ph = p_h
        adjustments = []

        # 1. Referee Impact
        if referee and referee in self.referee_impact:
            ref_impact = self.referee_impact[referee]
            # Negative impact means ref suppresses home advantage
            # Convert xG diff to probability adjustment (empirical scaling)
            prob_adjustment = ref_impact * 0.15  # -0.5 xG diff = -7.5% home win prob
            p_h += prob_adjustment
            p_a -= prob_adjustment
            adjustments.append(f"Referee {referee}: {prob_adjustment:+.3f}")

        # 2. Team Regime Classification
        home_regime = self.team_regimes.get(h_name, 0)
        away_regime = self.team_regimes.get(a_name, 0)

        # Clinical teams (positive xG diff) win more often than xG suggests
        # Wasteful teams (negative xG diff) win less often
        if home_regime != 0:
            regime_adj = home_regime * 0.20  # 0.15 xG diff = +3% win prob
            p_h += regime_adj
            p_d -= regime_adj * 0.5
            p_a -= regime_adj * 0.5
            adjustments.append(f"Home regime ({home_regime:+.3f}): {regime_adj:+.3f}")

        if away_regime != 0:
            regime_adj = away_regime * 0.20
            p_a += regime_adj
            p_d -= regime_adj * 0.5
            p_h -= regime_adj * 0.5
            adjustments.append(f"Away regime ({away_regime:+.3f}): {regime_adj:+.3f}")

        # 3. Referee-Team Interaction
        if referee:
            h_interaction = self.interactions.get((h_name, referee), 0)
            a_interaction = self.interactions.get((a_name, referee), 0)

            if h_interaction != 0:
                interaction_adj = h_interaction * 0.10  # -1.0 xG diff = -10% win prob
                p_h += interaction_adj
                p_d -= interaction_adj * 0.5
                p_a -= interaction_adj * 0.5
                adjustments.append(f"Home-Ref interaction: {interaction_adj:+.3f}")

            if a_interaction != 0:
                interaction_adj = a_interaction * 0.10
                p_a += interaction_adj
                p_d -= interaction_adj * 0.5
                p_h -= interaction_adj * 0.5
                adjustments.append(f"Away-Ref interaction: {interaction_adj:+.3f}")

        # Normalize probabilities to sum to 1.0
        total = p_h + p_d + p_a
        p_h /= total
        p_d /= total
        p_a /= total

        # Calculate total adjustment
        total_adj = p_h - original_ph

        return p_h, p_d, p_a, total_adj, adjustments

def run_v4_enhanced_backtest():
    print("--- [GRAPH-ENHANCED] Soccer Engine V4+ ---")
    mapping_path = "soccer_data/processed/team_name_mapping.json"
    insights_path = "soccer_data/processed/graph_insights.json"

    engine = SoccerEngineV4Enhanced(mapping_path, insights_path)

    # 1. Load Match Data
    results_files = glob.glob("soccer_data/raw_data/understat/*/202*/results.json")
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
    odds_df = pd.concat([pd.read_csv(f, encoding='unicode_escape') for f in glob.glob("soccer_data/raw_data/historical_odds/*.csv")])

    # 4. Load Referee Data (if available)
    # For now, we'll use None for referee since we don't have match-referee mapping in current data
    # In production, this would come from a referee assignment dataset

    results = []
    for idx, row in df.iterrows():
        h_exp = get_rolling(row['h_name'], row['datetime'])
        a_exp = get_rolling(row['a_name'], row['datetime'])
        if h_exp is None or a_exp is None: continue

        # Base probability calculation
        p_h, p_d, p_a = engine.calculate_probs(h_exp, a_exp)

        # Apply graph intelligence (referee=None for now, would need match-referee data)
        p_h_adj, p_d_adj, p_a_adj, total_adj, adjustments = engine.apply_graph_intelligence(
            p_h, p_d, p_a,
            row['h_name'],
            row['a_name'],
            referee=None  # Would use actual referee if available
        )

        # Match Odds
        h_mapped = engine.mapping.get(row['h_name'])
        a_mapped = engine.mapping.get(row['a_name'])
        if not h_mapped or not a_mapped: continue

        m_odds = odds_df[(odds_df['HomeTeam'] == h_mapped) & (odds_df['AwayTeam'] == a_mapped)].head(1)
        if not m_odds.empty:
            o_h, o_d, o_a = m_odds['AvgH'].values[0], m_odds['AvgD'].values[0], m_odds['AvgA'].values[0]

            # Calculate edges (for analysis)
            edges_base = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}
            edges_adj = {'h': p_h_adj - (1/o_h), 'd': p_d_adj - (1/o_d), 'a': p_a_adj - (1/o_a)}

            # Bet on highest probability (FIXED strategy)
            probs_adj = {'h': p_h_adj, 'd': p_d_adj, 'a': p_a_adj}
            best = max(probs_adj, key=probs_adj.get)

            profit = 0
            if best == row['outcome']:
                profit = m_odds[f'Avg{best.upper()}'].values[0] - 1
            else:
                profit = -1

            results.append({
                "match": f"{row['h_name']} vs {row['a_name']}",
                "league": row['league'],
                "pred_base": max({'h':p_h, 'd':p_d, 'a':p_a}, key={'h':p_h, 'd':p_d, 'a':p_a}.get),
                "pred_enhanced": best,
                "p_h_base": p_h,
                "p_h_enhanced": p_h_adj,
                "adjustment": total_adj,
                "bet": best,
                "edge_base": edges_base[best],
                "edge_enhanced": edges_adj[best],
                "actual": row['outcome'],
                "profit": profit,
                "adjustments_applied": "; ".join(adjustments) if adjustments else "None"
            })

    output_df = pd.DataFrame(results)
    output_df.to_csv("soccer_data/processed/backtest_v4_enhanced.csv", index=False)

    print(f"\n{'='*60}")
    print("BACKTEST COMPLETE - V4 ENHANCED")
    print(f"{'='*60}")
    print(f"Sample Size: {len(output_df)}")
    print(f"\nBASE MODEL (No Graph Intelligence):")
    print(f"  Prediction Accuracy: {(output_df['pred_base'] == output_df['actual']).mean():.2%}")

    print(f"\nENHANCED MODEL (With Graph Intelligence):")
    print(f"  Prediction Accuracy: {(output_df['pred_enhanced'] == output_df['actual']).mean():.2%}")
    print(f"  Overall ROI: {output_df['profit'].mean():.2%}")

    print(f"\nIMPROVEMENT FROM GRAPH INTELLIGENCE:")
    base_roi = output_df['profit'].mean()
    # Would compare to V4 baseline if we had it loaded
    print(f"  Probability Adjustments Applied: {(output_df['adjustment'] != 0).sum()} matches")
    print(f"  Average Adjustment Magnitude: {output_df['adjustment'].abs().mean():.3f}")

    print(f"\nBY LEAGUE:")
    for league in output_df['league'].unique():
        league_df = output_df[output_df['league'] == league]
        roi = league_df['profit'].mean()
        accuracy = (league_df['pred_enhanced'] == league_df['actual']).mean()
        print(f"  {league:15s}: {roi:+6.2%} ROI, {accuracy:.1%} accuracy ({len(league_df)} bets)")

    print(f"\nOutput saved to: soccer_data/processed/backtest_v4_enhanced.csv")

if __name__ == "__main__":
    run_v4_enhanced_backtest()
