
import pandas as pd
import numpy as np

DATA_PATH = "processed/backtest_results_exp1.csv"
EDGE_CUTOFF = 50.0

def validate_upset_regime():
    print("🧪 Starting Experiment 3: Upset Regime Validation...")
    
    try:
        df = pd.read_csv(DATA_PATH)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 1. Filter: Edge < 50 (Underdog / Neutral Context)
    baseline_df = df[df['edge_score'] < EDGE_CUTOFF].copy()
    
    if baseline_df.empty:
        print("❌ No data for Edge < 50.")
        return
        
    # 2. Define Signals (TEAM Perspective)
    # We want to see if these signals help the Team win when Edge is low.
    
    # Fatigue: FRESH_ADV (Team has rest advantage)
    sig_fatigue = baseline_df['fatigue_state'] == 'FRESH_ADV'
    
    # Flow: STRONG_UP (Team is hot)
    sig_flow = baseline_df['flow_state'] == 'STRONG_UP'
    
    # Memory: DOMINATOR (Team owns Opponent historically)
    sig_memory = baseline_df['memory_state'] == 'DOMINATOR'
    
    # Luck: UNLUCKY (Team has been unlucky -> Reversion to Mean BOUNCE)
    # Note: Previous analysis showed Negative Correlation for Luck Score.
    # So High Score (LUCKY) -> Lose. Low Score (UNLUCKY) -> Win.
    sig_luck = baseline_df['luck_state'] == 'UNLUCKY'
    
    # Combined Signal (Any of the above)
    baseline_df['upset_signal'] = sig_fatigue | sig_flow | sig_memory | sig_luck
    
    # 3. Calculate Stats
    base_games = len(baseline_df)
    base_win = baseline_df['result'].mean()
    
    upset_df = baseline_df[baseline_df['upset_signal'] == True]
    upset_games = len(upset_df)
    upset_win = upset_df['result'].mean() if upset_games > 0 else 0.0
    
    no_upset_df = baseline_df[baseline_df['upset_signal'] == False]
    no_upset_games = len(no_upset_df)
    no_upset_win = no_upset_df['result'].mean() if no_upset_games > 0 else 0.0
    
    # 4. Output
    print("\n📊 Experiment 3 Results (Edge < 50 Only)")
    print(f"{'Bucket':<30} {'Games':<10} {'Win%':<10}")
    print("-" * 50)
    print(f"{'Baseline (All Edge < 50)':<30} {base_games:<10} {base_win*100:.1f}%")
    print(f"{'Upset Signal ON':<30} {upset_games:<10} {upset_win*100:.1f}%")
    print(f"{'Upset Signal OFF':<30} {no_upset_games:<10} {no_upset_win*100:.1f}%")
    print("-" * 50)
    
    lift = (upset_win - base_win) * 100
    
    print("\n🏁 Conclusion:")
    if upset_games < 50:
         print(f"⚠️ Sample size too small (<50). ({upset_games} games)")
    elif lift >= 5.0:
        print(f"✅ Upset Regime VALID. Lift: +{lift:.1f}% vs Baseline.")
    else:
        print(f"❌ Upset Regime INVALID. Lift: +{lift:.1f}% vs Baseline (Target +5%).")

if __name__ == "__main__":
    validate_upset_regime()
