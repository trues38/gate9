
import pandas as pd
import numpy as np
import sys

# CONFIG
DATA_PATH = "processed/backtest_results_exp1.csv"
TRAIN_CUTOFF = "2024-07-01" # Split 23-24 Season (Train) vs 24-25 Season (Test)
VECTORS = ['flow_score', 'fatigue_score', 'memory_score', 'luck_score']
EDGE_THRESHOLD = 60.0
TWIN_WIN_THRESHOLD = 0.60 # 3 out of 5

def validate_twin_engine():
    print("🧪 Starting Experiment 2: Twin Engine Validation (Strict)...")
    
    # 1. Load Data
    try:
        df = pd.read_csv(DATA_PATH)
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Strict Train/Test Split
    train_df = df[df['date'] < TRAIN_CUTOFF].copy().reset_index(drop=True)
    test_df = df[df['date'] >= TRAIN_CUTOFF].copy().reset_index(drop=True)
    
    print(f"📉 Train Set (2023-24): {len(train_df)} games")
    print(f"📈 Test Set (2024-25): {len(test_df)} games")
    
    if len(train_df) < 100 or len(test_df) < 50:
        print("❌ Insufficient data for validation.")
        return

    # 3. Vector Preparation
    # Convert to numpy arrays for fast broadcasting
    train_vecs = train_df[VECTORS].values
    train_results = train_df['result'].values # 0 or 1
    
    test_vecs = test_df[VECTORS].values
    
    print("🔍 Running Twin Search (Euclidean, Top-5)...")
    
    # 4. Run Search (Vectorized iteration)
    twin_signals = []
    
    for i in range(len(test_df)):
        query_vec = test_vecs[i]
        
        # Euclidean Distance
        # dists = sqrt(sum((x - y)^2))
        dists = np.sqrt(np.sum((train_vecs - query_vec)**2, axis=1))
        
        # Top 5 Indices
        nearest_indices = np.argsort(dists)[:5]
        
        # Outcomes
        outcomes = train_results[nearest_indices]
        twin_win_rate = np.mean(outcomes)
        
        # Signal
        is_active = twin_win_rate >= TWIN_WIN_THRESHOLD
        twin_signals.append(is_active)
        
    test_df['twin_active'] = twin_signals
    
    # 5. Evaluation Logic
    # Group A: Edge >= 60 (Baseline)
    # Group B: Edge >= 60 AND Twin Active
    # Group C: Twin Active Only (for context)
    
    baseline_mask = test_df['edge_score'] >= EDGE_THRESHOLD
    twin_mask = test_df['twin_active'] == True
    
    # Baseline
    df_base = test_df[baseline_mask]
    base_games = len(df_base)
    base_win = df_base['result'].mean() if base_games > 0 else 0.0
    
    # Combined (Edge + Twin)
    df_combined = test_df[baseline_mask & twin_mask]
    comb_games = len(df_combined)
    comb_win = df_combined['result'].mean() if comb_games > 0 else 0.0
    
    # Twin Only
    df_twin = test_df[twin_mask]
    twin_games = len(df_twin)
    twin_win = df_twin['result'].mean() if twin_games > 0 else 0.0
    
    # 6. Output Table
    print("\n📊 Experiment 2 Results")
    print(f"{'Bucket':<25} {'Games':<10} {'Win%':<10}")
    print("-" * 45)
    print(f"{'Edge >= 60 (Baseline)':<25} {base_games:<10} {base_win*100:.1f}%")
    print(f"{'Edge >= 60 + Twin ON':<25} {comb_games:<10} {comb_win*100:.1f}%")
    print(f"{'Twin ON only':<25} {twin_games:<10} {twin_win*100:.1f}%")
    print("-" * 45)
    
    # 7. Final Conclusion
    improvement = (comb_win - base_win) * 100
    print("\n🏁 Conclusion:")
    if comb_games < 50:
         print(f"⚠️ Sample size too small (<50) to conclude. ({comb_games} games)")
    elif improvement >= 3.0:
        print(f"✅ Twin Engine provides +{improvement:.1f}% additional predictive power over Edge.")
    else:
        print(f"❌ Twin Engine does NOT provide significant improvement ({improvement:+.1f}%). Strategy FAIL.")

if __name__ == "__main__":
    validate_twin_engine()
