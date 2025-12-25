
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nba_data.quant_engine.quant_core import QuantDataManager, TeamStrengthEngine, MomentumEngine, FatigueEngine, MatchupEngine, InjuryEngine

# Connect to DB
con = duckdb.connect("nba_analytics.duckdb")

def run_backtest(start_date="2025-10-22", end_date="2025-12-10"):
    print(f"🚀 Starting Backtest from {start_date} to {end_date}...")
    
    # Initialize Engines
    dm = QuantDataManager()
    tse = TeamStrengthEngine(dm)
    me = MomentumEngine(dm)
    fe = FatigueEngine(dm)
    ie = InjuryEngine(dm)
    matchup = MatchupEngine(tse, me, fe, ie)
    
    # Fetch All Completed Games in Period
    query = f"""
    SELECT game_id, date, home_team_id, away_team_id, home_score, away_score
    FROM fact_game
    WHERE date BETWEEN '{start_date}' AND '{end_date}'
    AND status = 'STATUS_FINAL'
    ORDER BY date
    """
    games = con.sql(query).df()
    
    print(f"🏀 Found {len(games)} games to backtest.")
    
    results = []
    
    for _, row in games.iterrows():
        gid = row['game_id']
        date_str = str(row['date']).split(' ')[0] # Strip time if present
        h_id = row['home_team_id']
        a_id = row['away_team_id']
        
        # Real Result
        h_score = row['home_score']
        a_score = row['away_score']
        real_margin = h_score - a_score # Positive = Home Win
        real_winner = h_id if real_margin > 0 else a_id
        
        # Run Prediction (Simulating 'Before the Game')
        # We must ensure the engines don't peek at accurate future data?
        # QuantDataManager uses window functions.
        # The 'get_team_momentum' query has "WHERE date < date_str". CORRECT.
        # Fatigue looks at past games. CORRECT.
        # Injury Report: Uses 'report_date'. If we have historical injury data, perfect.
        # If not, it might be empty or static.
        
        anal = matchup.analyze_matchup(h_id, a_id, date_str)
        
        if not anal:
            continue
            
        pred_spread = anal['projected_spread'] # Positive = Home Win Margin
        details = anal['details']
        
        # Determine Predicted Winner
        pred_winner = h_id if pred_spread > 0 else a_id
        is_correct = (pred_winner == real_winner)
        
        # Metrics
        err = abs(pred_spread - real_margin)
        
        results.append({
            "date": date_str,
            "game_id": gid,
            "home": h_id,
            "away": a_id,
            "real_margin": real_margin,
            "pred_spread": pred_spread,
            "error": err,
            "correct": is_correct,
            "net_edge": details['net_edge'],
            "mom_edge": details['mom_edge'],
            "fatigue_diff": details['fatigue_home'] - details['fatigue_away'],
            "injury_diff": details['injury_home'] - details['injury_away']
        })
        
    res_df = pd.DataFrame(results)
    
    # Analysis
    acc = res_df['correct'].mean()
    mae = res_df['error'].mean()
    
    print("\n📊 Backtest Results Summary")
    print("===========================")
    print(f"Total Games : {len(res_df)}")
    print(f"Accuracy    : {acc:.2%}")
    print(f"MAE (Spread): {mae:.2f} pts")
    
    # Layer Correlation Analysis
    # Does Net Rating predict Margin?
    corr_net = res_df['net_edge'].corr(res_df['real_margin'])
    corr_mom = res_df['mom_edge'].corr(res_df['real_margin'])
    corr_fat = res_df['fatigue_diff'].corr(res_df['real_margin']) * -1 # Negative correlation expected (Fatigue -> Lose)
    corr_inj = res_df['injury_diff'].corr(res_df['real_margin']) * -1 # Negative correlation expected
    
    print("\n🔍 Layer Correlations (with Real Margin)")
    print(f"Team Strength (NetRtg) : {corr_net:.3f}")
    print(f"Momentum (L5 NetRtg)   : {corr_mom:.3f}")
    print(f"Fatigue Impact         : {corr_fat:.3f}")
    print(f"Injury Impact          : {corr_inj:.3f}")
    
    # Save Report
    res_df.to_csv("backtest_results_detailed.csv", index=False)
    print("\n✅ Detailed results saved to backtest_results_detailed.csv")

if __name__ == "__main__":
    run_backtest()
