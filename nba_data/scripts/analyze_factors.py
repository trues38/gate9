
import pandas as pd
import numpy as np
import sys

RESULTS_PATH = 'processed/backtest_results_exp1.csv'

def analyze():
    print("📊 Analyzing Backtest Results...")
    try:
        df = pd.read_csv(RESULTS_PATH)
    except FileNotFoundError:
        print(f"❌ Results file not found: {RESULTS_PATH}")
        return

    if df.empty:
        print("⚠️ Results file is empty.")
        return

    print(f"Loaded {len(df)} games.")

    factors = [
        ('flow_score', 'flow_state'),
        ('fatigue_score', 'fatigue_state'),
        ('memory_score', 'memory_state'),
        ('luck_score', 'luck_state'),
        ('tempo_score', 'tempo_state'),
        ('edge_score', None)
    ]

    summary_rows = []

    for score_col, state_col in factors:
        print(f"\n--- Analysis: {score_col.upper()} ---")
        
        # 1. Correlation
        corr = df[score_col].corr(df['margin'])
        print(f"Correlation to Margin: {corr:.4f}")
        
        # 2. Bucketing (if numerical score)
        # Create bins: 0, 1-5, 5-10, 10+
        # Adjust for edge_score (0-100) vs others (0-20)
        
        if score_col == 'edge_score':
            bins = [0, 40, 50, 60, 100]
            labels = ['Low (<40)', 'Neutral (40-50)', 'Advantage (50-60)', 'Dominant (60+)']
        else:
            bins = [-1, 0.1, 5, 10, 99]
            labels = ['Neutral (0)', 'Low (1-5)', 'Med (5-10)', 'High (10+)']
            
        try:
            df['bin'] = pd.cut(df[score_col].abs(), bins=bins, labels=labels)
            
            grouped = df.groupby('bin').agg({
                'result': ['count', 'mean'],
                'margin': 'mean'
            })
            grouped.columns = ['Games', 'Win%', 'AvgMargin']
            
            print(grouped)
            
            # 3. State Analysis (if available)
            if state_col:
                print(f"\nState Breakdown ({state_col}):")
                state_grp = df.groupby(state_col).agg({
                    'result': ['count', 'mean'],
                    'margin': 'mean'
                })
                state_grp.columns = ['Games', 'Win%', 'AvgMargin']
                print(state_grp.sort_values('Win%', ascending=False))

            # Store summary
            summary_rows.append({
                'Factor': score_col,
                'Correlation': corr,
                'High_Bucket_Win%': grouped.loc['High (10+)', 'Win%'] if 'High (10+)' in grouped.index else pd.NA
            })

        except Exception as e:
            print(f"Error analyzing {score_col}: {e}")

    print("\n\n=== FACTOR RANKING (Predictive Power) ===")
    summ_df = pd.DataFrame(summary_rows).sort_values('Correlation', ascending=False)
    print(summ_df)

if __name__ == "__main__":
    analyze()
