import sys
import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

CLUSTERS_FILE = "regime_zero/data/regime_clusters.json"

def match_regime(current_vector):
    """
    Finds the closest regime for the current vector.
    Returns the matched regime and similarity score.
    """
    if not os.path.exists(CLUSTERS_FILE):
        print(f"❌ No clusters file found at {CLUSTERS_FILE}")
        return None, 0.0
        
    with open(CLUSTERS_FILE, "r") as f:
        regimes = json.load(f)
        
    best_score = -1.0
    best_regime = None
    
    # Calculate similarity with each centroid
    # Vector is 1D list, reshape to 2D for sklearn
    curr_vec = np.array(current_vector).reshape(1, -1)
    
    for regime in regimes:
        centroid = np.array(regime['centroid']).reshape(1, -1)
        score = cosine_similarity(curr_vec, centroid)[0][0]
        
        # Convert to percentage-like score (0-1)
        # Cosine similarity is -1 to 1. We assume vectors are somewhat aligned so 0-1 is typical.
        
        if score > best_score:
            best_score = score
            best_regime = regime
            
    return best_regime, best_score

if __name__ == "__main__":
    # Test with random vector
    vec = np.random.rand(1536).tolist()
    regime, score = match_regime(vec)
    if regime:
        print(f"✅ Matched Regime: {regime['name']} (Score: {score:.4f})")
        print(f"Regime Dates: {regime['dates']}")
