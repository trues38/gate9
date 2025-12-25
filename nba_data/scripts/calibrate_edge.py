
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

DATA_PATH = "processed/backtest_results_exp1.csv"
PLOT_PATH = "reports/edge_calibration_curve.png"

def calibrate_edge():
    print("🔬 Starting Edge Score Calibration Experiment...")
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: File not found at {DATA_PATH}")
        return
        
    df = pd.read_csv(DATA_PATH)
    
    # Ensure required columns exist
    if 'edge_score' not in df.columns or 'result' not in df.columns:
        print("❌ Error: Missing required columns (edge_score, result)")
        return
        
    # Drop NaNs
    df = df.dropna(subset=['edge_score', 'result'])
    
    print(f"✅ Loaded {len(df)} games for calibration.")
    
    # 2. Bucketize (5-point intervals)
    bins = range(0, 105, 5) # 0, 5, 10, ... 100
    labels = [f"{i}-{i+5}" for i in range(0, 100, 5)]
    
    # Use pd.cut
    df['bucket'] = pd.cut(df['edge_score'], bins=bins, right=False)
    
    # 3. Aggregate
    calib = df.groupby('bucket', observed=False).agg(
        games=('result', 'count'),
        wins=('result', 'sum'),
        win_rate=('result', 'mean')
    ).reset_index()
    
    # Calculate Standard Error (Walsh Formula or simple sqrt(p(1-p)/n))
    calib['std_error'] = np.sqrt(calib['win_rate'] * (1 - calib['win_rate']) / calib['games'])
    
    # Fill standard error 0 if games < 2 or win_rate 0/1
    calib['std_error'] = calib['std_error'].fillna(0.0)
    
    # 4. Output Table
    print("\n📊 Calibration Table")
    print("-" * 65)
    print(f"{'Edge Bucket':<15} | {'Games':<8} | {'Wins':<8} | {'Win Rate':<10} | {'Error':<8}")
    print("-" * 65)
    
    for _, row in calib.iterrows():
        # Clean bucket string
        b_str = str(row['bucket'])
        print(f"{b_str:<15} | {int(row['games']):<8} | {int(row['wins']):<8} | {row['win_rate']*100:>6.1f}%   | +/- {row['std_error']*100:.1f}%")
        
    print("-" * 65)
    
    # 5. Key Verification Questions
    print("\n🧠 Key Verification Questions")
    
    # Q1: Edge >= 60
    e60 = df[df['edge_score'] >= 60]
    wr60 = e60['result'].mean() * 100 if len(e60) > 0 else 0.0
    print(f"1. Edge >= 60 Win Rate: {wr60:.1f}% ({len(e60)} games)")
    
    # Q2: Edge >= 70
    e70 = df[df['edge_score'] >= 70]
    wr70 = e70['result'].mean() * 100 if len(e70) > 0 else 0.0
    print(f"2. Edge >= 70 Win Rate: {wr70:.1f}% ({len(e70)} games)")
    
    # Q3: Edge <= 40
    e40 = df[df['edge_score'] <= 40]
    wr40 = e40['result'].mean() * 100 if len(e40) > 0 else 0.0
    print(f"3. Edge <= 40 Win Rate: {wr40:.1f}% ({len(e40)} games)")
    
    # Q4: Edge ~ 50 (45-55)
    e50 = df[(df['edge_score'] >= 45) & (df['edge_score'] < 55)]
    wr50 = e50['result'].mean() if len(e50) > 0 else 0.0
    print(f"4. Edge ~ 50 Win Rate:  {wr50*100:.1f}% ({len(e50)} games) -> {'Converged' if 0.45 <= wr50 <= 0.55 else 'Drifted'}")
    
    # Q5: Monotonic Check
    # Check correlation between bucket midpoint and win rate
    calib['midpoint'] = calib['bucket'].apply(lambda x: x.mid).astype(float)
    # Filter empty buckets
    valid_calib = calib[calib['games'] > 10]
    corr = valid_calib['midpoint'].corr(valid_calib['win_rate'])
    print(f"5. Monotonic Correlation: {corr:.4f} (Target > 0.9)")
    
    # 6. Production Mapping Table (55+)
    print("\n🏭 Production Mapping Table (High Confidence)")
    print(f"{'Edge Range':<15} | {'Empirical Prob'}")
    print("-" * 35)
    
    ranges = [(55,59), (60,64), (65,69), (70,74), (75,79), (80, 100)]
    
    for low, high in ranges:
        mask = (df['edge_score'] >= low) & (df['edge_score'] <= high)
        sub = df[mask]
        wr = sub['result'].mean() if len(sub) > 0 else 0.0
        r_str = f"{low}-{high}" if high < 100 else f"{low}+"
        print(f"{r_str:<15} | {wr*100:.1f}% ({len(sub)} gms)")
        
    print("-" * 35)

    # 7. Plotting
    try:
        plt.figure(figsize=(10, 6))
        # Plot data points
        plt.errorbar(calib['midpoint'], calib['win_rate'], yerr=calib['std_error'], fmt='o-', label='Empirical Win Rate')
        # Reference line
        plt.axhline(0.5, color='gray', linestyle='--', label='Neutral (50%)')
        plt.axvline(60, color='red', linestyle='--', label='Production Cutoff (60)')
        
        plt.title('Edge Score Calibration Curve')
        plt.xlabel('Edge Score')
        plt.ylabel('Home Win Probability')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.ylim(0, 1.0)
        
        plt.savefig(PLOT_PATH)
        print(f"\n📈 Calibration Plot saved to {PLOT_PATH}")
    except Exception as e:
        print(f"⚠️ plotting failed: {e}")

if __name__ == "__main__":
    calibrate_edge()
