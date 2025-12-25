
import json
import argparse
import pandas as pd
import numpy as np
import os

def load_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)

def main():
    PRE_FILE = "nba_betting_report/backtest/pre_edge_results.jsonl"
    STRUCT_FILE = "nba_betting_report/regime_observations.jsonl"
    OUTPUT_DIR = "nba_betting_report/backtest"
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("🚀 Loading Data...")
    
    # 1. Load Pre-Game Predictions
    pre_df = load_jsonl(PRE_FILE)
    pre_df = pre_df.rename(columns={'pre_edge_score': 'pre_score'})
    print(f"  Pre-Game Predictions: {len(pre_df)}")
    
    # 2. Load Post-Game Truth
    struct_df = load_jsonl(STRUCT_FILE)
    # Extract score_margin from box_stats if available
    struct_df['score_margin'] = struct_df['box_stats'].apply(lambda x: x.get('score_margin', 0))
    struct_df = struct_df.rename(columns={'edge_score': 'struct_score'})
    print(f"  Structural Ground Truth: {len(struct_df)}")
    
    # 3. Merge
    merged = pd.merge(pre_df, struct_df[['game_id', 'struct_score', 'score_margin']], on='game_id', how='inner')
    print(f"  Merged Analysis Set: {len(merged)}")
    
    # --- Analysis 1: Monotonicity (Deciles) ---
    merged['pre_decile'] = pd.qcut(merged['pre_score'], 10, labels=False)
    
    decile_stats = merged.groupby('pre_decile').agg(
        avg_pre=('pre_score', 'mean'),
        avg_struct=('struct_score', 'mean'),
        avg_margin=('score_margin', 'mean'),
        count=('game_id', 'count')
    ).reset_index().sort_values('pre_decile', ascending=False)
    
    
    # --- Analysis 2: Separation (Top 20% vs Bottom 20%) ---
    top_20_thresh = merged['pre_score'].quantile(0.8)
    bot_20_thresh = merged['pre_score'].quantile(0.2)
    
    top_20 = merged[merged['pre_score'] >= top_20_thresh]
    bot_20 = merged[merged['pre_score'] <= bot_20_thresh]
    
    # Blowout Rate (Margin >= 15)
    top_blowout = (top_20['score_margin'] >= 15).mean()
    bot_blowout = (bot_20['score_margin'] >= 15).mean()
    
    # Close Game Rate (Margin <= 5)
    top_close = (top_20['score_margin'] <= 5).mean()
    bot_close = (bot_20['score_margin'] <= 5).mean()
    
    
    # --- Analysis 3: Failure Cases ---
    # High Pre-Game (Top 20%) BUT Low Structural (Bottom 30% of Struct Score)
    # Struct Bottom 30% Thresh
    struct_bot_30 = merged['struct_score'].quantile(0.3)
    
    failures = merged[
        (merged['pre_score'] >= top_20_thresh) & 
        (merged['struct_score'] <= struct_bot_30)
    ]
    
    # --- Reporting ---
    summary_path = os.path.join(OUTPUT_DIR, "pre_game_backtest_summary.md")
    csv_path = os.path.join(OUTPUT_DIR, "pre_edge_vs_structural.csv")
    
    merged.to_csv(csv_path, index=False)
    
    with open(summary_path, 'w') as f:
        f.write("# Pre-Game Engine Backtest Summary\n\n")
        f.write("This backtest evaluates structural consistency, not prediction accuracy.\n")
        f.write("No outcome-based features were used in pre-game scoring.\n\n")
        
        f.write(f"Total Analyzed Games: {len(merged)}\n\n")
        
        f.write("## 1. Monotonicity (Decile Analysis)\n")
        f.write(decile_stats.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 2. Separation Power\n")
        f.write("| Segment | Blowout Rate (>=15) | Close Game Rate (<=5) |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| Top 20% (Pre >= {top_20_thresh:.1f}) | {top_blowout:.1%} | {top_close:.1%} |\n")
        f.write(f"| Bottom 20% (Pre <= {bot_20_thresh:.1f}) | {bot_blowout:.1%} | {bot_close:.1%} |\n")
        f.write("\n\n")
        
        f.write("## 3. Structural Failures (High Pre-Edge but Low Structural Support)\n")
        f.write(f"Definition: Pre-Edge Top 20% AND Structural Edge Bottom 30% (<= {struct_bot_30:.1f})\n")
        f.write(f"Count: {len(failures)}\n\n")
        
        if not failures.empty:
            f.write(failures[['game_id', 'pre_score', 'struct_score', 'score_margin']].to_markdown(index=False))
            
    print(f"✅ Pre-Game Backtest Complete. Report at {summary_path}")

if __name__ == "__main__":
    main()
