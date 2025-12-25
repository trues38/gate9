
import pandas as pd
import numpy as np
from scipy import stats

INPUT_PATH = "processed/nba_validation_dataset.csv"

def check_correlation():
    print("📉 Loading Data...")
    df = pd.read_csv(INPUT_PATH)
    
    # 1. Calc Implied Probability from Team Odds
    # Odds are Decimal. Prob = 1 / Odds
    df['r_odds_team'] = pd.to_numeric(df['r_odds_team'], errors='coerce')
    df['edge_score'] = pd.to_numeric(df['edge_score'], errors='coerce')
    
    # Drop NA
    df = df.dropna(subset=['r_odds_team', 'edge_score'])
    
    # Filter valid odds (> 1.0)
    df = df[df['r_odds_team'] > 1.0].copy()
    
    df['mkt_prob'] = 1.0 / df['r_odds_team']
    
    # Scale Edge Score to 0-1 for apples-to-apples comparison?
    # Edge 50 = 50%, Edge 100 = 100% (roughly)
    df['model_prob'] = df['edge_score'] / 100.0
    
    # 2. Pearson (Linear)
    pearson_corr, _ = stats.pearsonr(df['model_prob'], df['mkt_prob'])
    
    # 3. Spearman (Rank)
    spearman_corr, _ = stats.spearmanr(df['model_prob'], df['mkt_prob'])
    
    print(f"\n📊 CORRELATION REPORT (N={len(df)})")
    print(f"--------------------------------")
    print(f"⚡ Pearson (Linear):   {pearson_corr:.4f}")
    print(f"🔃 Spearman (Rank):    {spearman_corr:.4f}")
    
    # 4. Interpretation
    if pearson_corr > 0.9:
        print("\n🚨 CRITICAL: > 0.90 implies Model is mimicking Market.")
    elif pearson_corr > 0.7:
        print("\n✅ HEALTHY: 0.7-0.9 implies strong agreement but distinct signal.")
    else:
        print("\n⚠️ DIVERGENT: < 0.7 implies Model ignores Market.")
        
if __name__ == "__main__":
    check_correlation()
