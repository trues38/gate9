import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json
import os

def classify_soccer_regimes(backtest_csv_path):
    """
    Uses unsupervised learning (K-Means) to classify soccer matches into 'Regimes'.
    Regimes: 'Public Consensus', 'Upset Territory', 'High Volatility', etc.
    """
    if not os.path.exists(backtest_csv_path):
        return
    
    df = pd.read_csv(backtest_csv_path)
    if df.empty: return

    # Features for Regime Clustering
    # 1. Edge Strength
    # 2. Market Odd (Risk Level)
    # 3. xG Gap
    df['xg_gap'] = abs(df['h_xg'] - df['a_xg'])
    
    features = ['market_odd_h', 'xg_prob_h', 'edge', 'xg_gap']
    X = df[features]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 4 Regimes Strategy
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['regime_id'] = kmeans.fit_predict(X_scaled)
    
    # Map Regime IDs to descriptive names based on centroids
    # (Simplified for demo)
    regime_map = {
        0: "Heavy Favorite (Low Edge)",
        1: "Upset Opportunity (High Edge)",
        2: "Balanced Battle",
        3: "High Volatility / Outlier"
    }
    df['regime_name'] = df['regime_id'].map(regime_map)
    
    df.to_csv("soccer_data/processed/regime_classified_results.csv", index=False)
    print(f"ML Regime Classification complete. 4 Regimes detected.")
    
    # Summary of Edge per Regime
    summary = df.groupby('regime_name')['edge'].mean().to_dict()
    print("Average Edge by Regime:")
    for name, val in summary.items():
        print(f"  {name}: {val:.4f}")

if __name__ == "__main__":
    # pip install scikit-learn
    classify_soccer_regimes("soccer_data/processed/backtest_results.csv")
