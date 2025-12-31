import pandas as pd
import json
import glob
import os

def calculate_implied_probability(odds):
    return 1 / odds

def calculate_xg_probability(h_xg, a_xg):
    """
    Simplified Poisson or Normal distribution for win probability.
    Using a crude ratio for edge calculation demo.
    """
    total_xg = h_xg + a_xg
    if total_xg == 0: return 0.33, 0.33, 0.33
    
    # Crude conversion for demo: 
    # In practice, use Poisson distribution to calculate P(H), P(D), P(A)
    return h_xg / total_xg, 0.25, a_xg / total_xg

def run_soccer_backtest():
    """
    Matches Understat xG data with Historical Odds to find 'Edges'.
    """
    results_files = glob.glob("soccer_data/raw_data/understat/*/2024/results.json")
    odds_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    
    # Load all odds into a single dataframe for easy lookup
    odds_df_list = []
    for f in odds_files:
        temp_df = pd.read_csv(f, encoding='unicode_escape')
        # Normalize date format if needed
        odds_df_list.append(temp_df)
    
    all_odds = pd.concat(odds_df_list)
    
    backtest_results = []
    
    for rf in results_files:
        with open(rf, 'r') as f:
            matches = json.load(f)
        
        for m in matches:
            h_team = m['h']['title']
            a_team = m['a']['title']
            h_xg = float(m['xG']['h'])
            a_xg = float(m['xG']['a'])
            
            # Find matching odds record (using name normalization in real impl)
            # For now, simple string match attempt
            match_odds = all_odds[
                (all_odds['HomeTeam'].str.contains(h_team[:5])) & 
                (all_odds['AwayTeam'].str.contains(a_team[:5]))
            ].head(1)
            
            if not match_odds.empty:
                avg_h_odds = match_odds['AvgH'].values[0]
                market_prob = calculate_implied_probability(avg_h_odds)
                xg_prob_h, _, _ = calculate_xg_probability(h_xg, a_xg)
                
                edge = xg_prob_h - market_prob
                
                # Derive outcome from goals
                h_goals = int(m['goals']['h'])
                a_goals = int(m['goals']['a'])
                if h_goals > a_goals: outcome = 'h'
                elif a_goals > h_goals: outcome = 'a'
                else: outcome = 'd'

                backtest_results.append({
                    "match": f"{h_team} vs {a_team}",
                    "h_xg": h_xg,
                    "a_xg": a_xg,
                    "market_odd_h": avg_h_odds,
                    "market_prob_h": round(market_prob, 3),
                    "xg_prob_h": round(xg_prob_h, 3),
                    "edge": round(edge, 3),
                    "outcome": outcome
                })

    df_results = pd.DataFrame(backtest_results)
    output_path = "soccer_data/processed/backtest_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_results.to_csv(output_path, index=False)
    
    print(f"Backtest complete. Analyzed {len(df_results)} matches.")
    if len(df_results) > 0:
        print(f"Average Edge Found: {df_results['edge'].mean():.4f}")

if __name__ == "__main__":
    run_soccer_backtest()
