import sys
import os
import json
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

INPUT_FILE = "regime_zero/data/history_vectors.jsonl"
OUTPUT_CLUSTERS = "regime_zero/data/regime_clusters.json"

def cluster_regimes(n_clusters=5):
    """
    Clusters the historical vectors into regimes.
    """
    print(f"🌌 [Regime Zero] Clustering History into {n_clusters} Regimes...")
    
    dates = []
    vectors = []
    prompts = []
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ No history file found at {INPUT_FILE}")
        return
        
    with open(INPUT_FILE, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                dates.append(data['date'])
                vectors.append(data['vector'])
                prompts.append(data.get('prompt_preview', ''))
            except Exception as e:
                print(f"Skipping bad line: {e}")
                
    if not vectors:
        print("❌ No vectors found.")
        return
        
    X = np.array(vectors)
    print(f"Loaded {len(X)} vectors. Running KMeans...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X)
    
    # Analyze Clusters
    regimes = []
    for i in range(n_clusters):
        cluster_indices = np.where(labels == i)[0]
        cluster_dates = [dates[idx] for idx in cluster_indices]
        centroid = kmeans.cluster_centers_[i].tolist()
        
        print(f"\nRegime {i}: {len(cluster_dates)} episodes")
        print(f"Dates: {cluster_dates[:5]} ...")
        
        regimes.append({
            "id": i,
            "name": f"Regime {i} (Auto-Generated)", # Placeholder for LLM Labeling
            "count": len(cluster_dates),
            "dates": cluster_dates,
            "centroid": centroid
        })
        
    # Save
    with open(OUTPUT_CLUSTERS, "w") as f:
        json.dump(regimes, f, indent=2)
        
    print(f"\n✅ Saved {n_clusters} regimes to {OUTPUT_CLUSTERS}")

if __name__ == "__main__":
    cluster_regimes()
