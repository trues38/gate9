#!/usr/bin/env python3
"""
Soccer Engine V5 - Graph Intelligence + Injury Impact
V4 + 부상 영향 반영
"""

import pandas as pd
import numpy as np
from scipy.stats import poisson
import json
import glob
import os
from datetime import datetime, timedelta
import random

class SoccerEngineV5:
    def __init__(self, mapping_path, graph_insights_path, injury_simulation=True):
        with open(mapping_path, 'r') as f:
            self.mapping = json.load(f)

        # Load graph intelligence
        with open(graph_insights_path, 'r') as f:
            insights = json.load(f)

            # Team regimes (xG over/under-performance)
            self.team_regimes = {}
            for team_data in insights.get('team_regimes', []):
                self.team_regimes[team_data['team']] = team_data['xg_diff']

        # Injury simulation mode (실제 데이터 없으므로 시뮬레이션)
        self.injury_simulation = injury_simulation
        self.simulated_injuries = {}

    def calculate_probs(self, h_exp, a_exp, rho=-0.1):
        """Dixon-Coles adjusted Poisson"""
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

        p_h = np.sum(np.tril(m, -1))
        p_d = np.sum(np.diag(m))
        p_a = np.sum(np.triu(m, 1))

        return p_h, p_d, p_a

    def apply_team_regime_adjustment(self, p_h, p_d, p_a, h_team, a_team):
        """팀 체제 조정 (V4)"""
        h_regime = self.team_regimes.get(h_team, 0)
        a_regime = self.team_regimes.get(a_team, 0)

        scaling = 0.20

        if h_regime != 0:
            adjustment = h_regime * scaling
            p_h += adjustment
            p_d -= adjustment * 0.5
            p_a -= adjustment * 0.5

        if a_regime != 0:
            adjustment = a_regime * scaling
            p_a += adjustment
            p_d -= adjustment * 0.5
            p_h -= adjustment * 0.5

        # Normalize
        total = p_h + p_d + p_a
        p_h /= total
        p_d /= total
        p_a /= total

        return p_h, p_d, p_a

    def simulate_injury_for_match(self, match_date, h_team, a_team):
        """
        경기별 부상 시뮬레이션

        시뮬레이션 가정:
        - 15%의 경기에서 홈팀 주요 선수 부상
        - 15%의 경기에서 원정팀 주요 선수 부상
        - 부상 선수는 3-4주 결장
        """
        home_injuries = 0
        away_injuries = 0

        # 시뮬레이션: 15% 확률로 주요 선수 부상
        if random.random() < 0.15:
            home_injuries = 1  # Critical 선수 1명 부상

        if random.random() < 0.15:
            away_injuries = 1  # Critical 선수 1명 부상

        return home_injuries, away_injuries

    def apply_injury_adjustment(self, p_h, p_d, p_a, home_injuries, away_injuries):
        """
        부상 영향 반영

        조정 로직:
        - Critical 부상 1명당 -5%p 승률
        - 무승부 확률로 재분배
        """
        adjustment_per_injury = 0.05

        # 홈팀 부상 영향
        if home_injuries > 0:
            p_h -= home_injuries * adjustment_per_injury
            p_d += home_injuries * adjustment_per_injury * 0.6
            p_a += home_injuries * adjustment_per_injury * 0.4

        # 원정팀 부상 영향
        if away_injuries > 0:
            p_a -= away_injuries * adjustment_per_injury
            p_d += away_injuries * adjustment_per_injury * 0.6
            p_h += away_injuries * adjustment_per_injury * 0.4

        # Normalize
        total = p_h + p_d + p_a
        if total > 0:
            p_h /= total
            p_d /= total
            p_a /= total

        return p_h, p_d, p_a

def run_v5_backtest():
    print("=" * 60)
    print("Soccer Engine V5 - Graph + Injury Impact")
    print("=" * 60)

    mapping_path = "processed/team_name_mapping.json"
    graph_path = "processed/graph_insights.json"

    engine = SoccerEngineV5(mapping_path, graph_path, injury_simulation=True)

    print(f"\n✅ Loaded {len(engine.team_regimes)} team regime adjustments")
    print(f"✅ Injury simulation: ENABLED")

    # Set random seed for reproducibility
    random.seed(42)

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
    regime_adjustments = 0
    injury_adjustments = 0

    print(f"\n🔄 Running V5 backtest with injury simulation...")

    for idx, row in df.iterrows():
        h_exp = get_rolling(row['h_name'], row['datetime'])
        a_exp = get_rolling(row['a_name'], row['datetime'])
        if h_exp is None or a_exp is None: continue

        # Base probability
        p_h, p_d, p_a = engine.calculate_probs(h_exp, a_exp)
        p_h_base, p_d_base, p_a_base = p_h, p_d, p_a

        # Apply team regime adjustment (V4)
        p_h, p_d, p_a = engine.apply_team_regime_adjustment(
            p_h, p_d, p_a,
            row['h_name'],
            row['a_name']
        )

        if abs(p_h - p_h_base) > 0.001:
            regime_adjustments += 1

        # Apply injury adjustment (V5)
        home_injuries, away_injuries = engine.simulate_injury_for_match(
            row['datetime'],
            row['h_name'],
            row['a_name']
        )

        p_h_before_injury = p_h
        p_h, p_d, p_a = engine.apply_injury_adjustment(
            p_h, p_d, p_a,
            home_injuries,
            away_injuries
        )

        if abs(p_h - p_h_before_injury) > 0.001:
            injury_adjustments += 1

        # Match Odds
        h_mapped = engine.mapping.get(row['h_name'])
        a_mapped = engine.mapping.get(row['a_name'])
        if not h_mapped or not a_mapped: continue

        m_odds = odds_df[(odds_df['HomeTeam'] == h_mapped) & (odds_df['AwayTeam'] == a_mapped)].head(1)
        if not m_odds.empty:
            o_h, o_d, o_a = m_odds['AvgH'].values[0], m_odds['AvgD'].values[0], m_odds['AvgA'].values[0]

            # Calculate edges
            edges = {'h': p_h - (1/o_h), 'd': p_d - (1/o_d), 'a': p_a - (1/o_a)}

            # Bet on highest probability
            probs = {'h': p_h, 'd': p_d, 'a': p_a}
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
                "p_h_base": p_h_base,
                "p_h_final": p_h,
                "regime_adj": p_h_before_injury - p_h_base,
                "injury_adj": p_h - p_h_before_injury,
                "home_injuries": home_injuries,
                "away_injuries": away_injuries
            })

    output_df = pd.DataFrame(results)
    output_df.to_csv("processed/backtest_v5_with_injuries.csv", index=False)

    print(f"\n" + "=" * 60)
    print("RESULTS - V5 + Injury Impact")
    print("=" * 60)

    print(f"\nSample Size: {len(output_df)}")
    print(f"Regime Adjustments Applied: {regime_adjustments} matches ({regime_adjustments/len(output_df)*100:.1f}%)")
    print(f"Injury Adjustments Applied: {injury_adjustments} matches ({injury_adjustments/len(output_df)*100:.1f}%)")
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

    # Injury impact analysis
    print(f"\n" + "-" * 60)
    print("Injury Impact Analysis:")
    print("-" * 60)

    with_injury = output_df[(output_df['home_injuries'] > 0) | (output_df['away_injuries'] > 0)]
    without_injury = output_df[(output_df['home_injuries'] == 0) & (output_df['away_injuries'] == 0)]

    print(f"\nMatches with injuries: {len(with_injury)} ({len(with_injury)/len(output_df)*100:.1f}%)")
    print(f"  ROI: {with_injury['profit'].mean():+.2%}")
    print(f"  Accuracy: {(with_injury['pred'] == with_injury['actual']).mean():.1%}")

    print(f"\nMatches without injuries: {len(without_injury)} ({len(without_injury)/len(output_df)*100:.1f}%)")
    print(f"  ROI: {without_injury['profit'].mean():+.2%}")
    print(f"  Accuracy: {(without_injury['pred'] == without_injury['actual']).mean():.1%}")

    print(f"\nOutput saved to: processed/backtest_v5_with_injuries.csv")

    return output_df

if __name__ == "__main__":
    result_df = run_v5_backtest()
