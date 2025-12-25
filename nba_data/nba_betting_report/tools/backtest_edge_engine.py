
import json
import argparse
import pandas as pd
import numpy as np
import os

def load_data(input_file):
    data = []
    with open(input_file, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)

def analyze_deciles(df):
    """
    Q1: Does Edge Score distinguish game quality?
    Analysis by Decile
    """
    # Create Deciles
    df['edge_decile'] = pd.qcut(df['edge_score'], 10, labels=False)
    
    # Extract Score Margin from box_stats
    # Note: Structural Analyst puts 'score_margin' in box_stats
    df['score_margin'] = df['box_stats'].apply(lambda x: x.get('score_margin', 0))
    
    # Group by Decile
    grouped = df.groupby('edge_decile').agg(
        avg_edge=('edge_score', 'mean'),
        avg_margin=('score_margin', 'mean'),
        games=('game_id', 'count'),
        # Blowout: margin >= 15
        blowout_rate=('score_margin', lambda x: (x >= 15).mean()),
        # Close Game: margin <= 5
        close_rate=('score_margin', lambda x: (x <= 5).mean())
    ).reset_index()
    
    return grouped.sort_values('edge_decile', ascending=False)

def analyze_action(df):
    """
    Q2: Is BET/PASS judgment rational?
    """
    df['score_margin'] = df['box_stats'].apply(lambda x: x.get('score_margin', 0))
    
    grouped = df.groupby('action').agg(
        games=('game_id', 'count'),
        avg_margin=('score_margin', 'mean'),
        blowout_rate=('score_margin', lambda x: (x >= 15).mean()),
        close_rate=('score_margin', lambda x: (x <= 5).mean()),
        margin_std=('score_margin', 'std')
    ).reset_index()
    
    return grouped

def analyze_confidence(df):
    """
    Q3: Does confidence match volatility?
    """
    df['score_margin'] = df['box_stats'].apply(lambda x: x.get('score_margin', 0))
    
    grouped = df.groupby('confidence').agg(
        games=('game_id', 'count'),
        avg_margin=('score_margin', 'mean'),
        margin_std=('score_margin', 'std'),
        avg_edge=('edge_score', 'mean')
    ).reset_index()
    
    return grouped

def detect_upsets(df):
    """
    Find 'Upset' candidates: High Edge Score but Low Margin (or Loss)
    Since we don't track Win/Loss prediction explicitly (structural only),
    we define 'Upset' as: 
       - Top 20% Edge Score
       - AND (Margin <= 5 OR negative structural indicators?)
    
    Actually user defined Upset as:
      - Edge Score Top 20%
      - AND (Score Margin <= 3 OR Loss?) 
      
    Wait, 'Loss' is tricky without betting side. 
    We assumed BET is usually on the 'Home' side for v0.1 in Market Decision stub.
    Market Decision: side="home" (fixed stub).
    So if Home loses, it's a loss.
    
    Let's check side.
    """
    df['score_margin'] = df['box_stats'].apply(lambda x: x.get('score_margin', 0))
    
    # Approximate top 20% threshold
    threshold = df['edge_score'].quantile(0.8)
    
    upsets = []
    
    for idx, row in df.iterrows():
        # Check if high edge
        if row['edge_score'] >= threshold:
            # Check result
            # We need to know who won.
            # Structural Analyst output "scores": {"home": X, "away": Y}
            # Wait, jsonl row has 'box_stats' which has 'score_margin' (abs).
            # We don't strictly know winner from JSONL unless we dig deeper or updated JSONL to include scores.
            # JSONL has 'box_stats' which was stored. 
            # Structural Analyst `box_stats` usually contains derived metrics, but maybe not raw scores?
            # Let's check `structural_analyst.py`. -> box_stats does NOT contain raw scores, only margin.
            # BUT! `batch_processor` saves `ctx['box_stats']`. 
            # `structural_analyst` returns `game_contexts` which HAS 'scores'. 
            # But `batch_processor` ONLY saved `box_stats`. 
            # Limitation: We only have ABSOLUTE margin in box_stats.
            # So we cannot determine "Loss".
            # Users request: "Upset defined as (score_margin <= 3 OR Loss)"
            # Adaptation: strict "Upset" as "margin <= 3" for now since we can't see Loss.
            # OR, we only detect "Structural Failure" = High Edge but Low Margin.
            
            margin = row['box_stats'].get('score_margin', 0)
            
            if margin <= 3:
                upsets.append({
                    "game_id": row['game_id'],
                    "edge_score": row['edge_score'],
                    "score_margin": margin,
                    "pace_est": row['box_stats'].get('pace_est'),
                    "reb_diff": row['box_stats'].get('reb_diff'),
                    "efg_diff": abs(row['box_stats'].get('home_efg_pct',0) - row['box_stats'].get('away_efg_pct',0))
                })
                
    return pd.DataFrame(upsets)

def generate_report(deciles, actions, confidence, upsets, output_dir):
    summary_path = os.path.join(output_dir, "summary.md")
    
    with open(summary_path, 'w') as f:
        f.write("# Backtest Summary Report\n\n")
        f.write(f"Total Games Analyzed: {deciles['games'].sum()}\n\n")
        
        f.write("## 1. Edge Score Analysis (Deciles)\n")
        f.write(deciles.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 2. Action Analysis\n")
        f.write(actions.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 3. Confidence Analysis\n")
        f.write(confidence.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 4. Potential Upsets (High Edge, Low Margin)\n")
        f.write(f"Count: {len(upsets)}\n")
        if not upsets.empty:
            f.write(upsets.head(10).to_markdown(index=False))
        f.write("\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to regime_observations.jsonl")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()
    
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        
    print(f"Loading data from {args.input}...")
    df = load_data(args.input)
    
    print("Running Decile Analysis...")
    deciles = analyze_deciles(df)
    deciles.to_csv(os.path.join(args.output, "edge_decile_analysis.csv"), index=False)
    
    print("Running Action Analysis...")
    actions = analyze_action(df)
    actions.to_csv(os.path.join(args.output, "action_analysis.csv"), index=False)
    
    print("Running Confidence Analysis...")
    conf = analyze_confidence(df)
    conf.to_csv(os.path.join(args.output, "confidence_analysis.csv"), index=False)
    
    print("Detecting Upsets...")
    upsets = detect_upsets(df)
    upsets.to_csv(os.path.join(args.output, "upset_cases.csv"), index=False)
    
    print("Generating Summary...")
    generate_report(deciles, actions, conf, upsets, args.output)
    
    print(f"✅ Backtest complete. Results in {args.output}")

if __name__ == "__main__":
    main()
