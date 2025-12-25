import json
import numpy as np
import pandas as pd
import os
import math

class VectorEngine:
    """
    Phase 27: Vector Regime Engine
    Uses 5-Dimensional Embeddings (Flow, Fatigue, Memory, Luck, Tempo)
    to find structural twins in historical data.
    """
    
    VECTOR_PATH = "processed/regime_vectors_v1.json"
    
    def __init__(self):
        self.vectors = []
        self.df = None
        self.index = None # Search Index (KDTree or similar)
        self.is_ready = False
        
        # Weights for Distance Calculation (importance of dimension)
        self.weights = np.array([
            1.0, # Flow
            1.2, # Fatigue (Slightly more important)
            1.0, # Memory
            1.5, # Luck (Very important for market context)
            0.8  # Tempo (Stylistic)
        ])
        
        self._load_vectors()
        
    def _load_vectors(self):
        """Load JSON and build search index"""
        if not os.path.exists(self.VECTOR_PATH):
            print(f"⚠️ Vector Store Missing: {self.VECTOR_PATH}")
            return
            
        print(f"📥 Loading Vector Store: {self.VECTOR_PATH}")
        try:
            with open(self.VECTOR_PATH, 'r') as f:
                self.vectors = json.load(f)
                
            if not self.vectors:
                return
                
            # Convert to DataFrame for easier math
            self.df = pd.DataFrame(self.vectors)
            
            # Extract Vector Matrix
            # Column 'v' is a list of 5 floats
            self.matrix = np.array(self.df['v'].tolist())
            
            # Normalize (Z-Score)
            # We save mean/std to normalize query vectors later
            self.mean = np.mean(self.matrix, axis=0)
            self.std = np.std(self.matrix, axis=0)
            
            # Avoid division by zero
            self.std[self.std == 0] = 1.0
            
            self.norm_matrix = (self.matrix - self.mean) / self.std
            
            # Apply Weights
            self.weighted_matrix = self.norm_matrix * self.weights
            
            self.is_ready = True
            print(f"✅ Vector Engine Ready: {len(self.vectors)} games indexed.")
            
        except Exception as e:
            print(f"❌ Vector Load Error: {e}")
            
    def find_twins(self, target_vector_raw, n=5):
        """
        Find N nearest neighbors for a given 5D vector.
        target_vector_raw: [Flow, Fatigue, Memory, Luck, Tempo] (Raw Scores)
        """
        if not self.is_ready:
            return []
            
        # 1. Normalize Target
        target = np.array(target_vector_raw)
        norm_target = (target - self.mean) / self.std
        weighted_target = norm_target * self.weights
        
        # 2. Calculate Distance (Euclidean)
        # Dist = sqrt(sum((A - B)^2))
        # More efficient: Scipy cdist or manual broadcasting
        
        diff = self.weighted_matrix - weighted_target
        dists = np.sqrt(np.sum(diff**2, axis=1))
        
        # 3. Sort
        # Get indices of top N
        sorted_indices = np.argsort(dists)
        top_n_indices = sorted_indices[:n]
        
        results = []
        for idx in top_n_indices:
            dist = dists[idx]
            match = self.vectors[idx]
            
            # Convert Distance to Similarity % (Heuristic)
            # Dist 0 = 100%, Dist 5 = 0%?
            # Let's say reasonable max distance is around 10.0
            sim_score = max(0, 100 - (dist * 10)) # Rough heuristic
            
            results.append({
                'game_id': match['id'],
                'date': match['date'],
                'matchup': f"{match['team']} vs {match['opp']}",
                'vector': match['v'],
                'distance': round(dist, 2),
                'similarity': round(sim_score, 1),
                'result_v': match['res'] # Did they win?
            })
            
        return results

if __name__ == "__main__":
    # Test
    ve = VectorEngine()
    # Dummy Vector: High Flow, Tired, Bad Matchup, Very Unlucky, Fast
    dummy = [6.9, -2.0, -5.0, -11.6, 5.0]
    print("Test Query:", dummy)
    twins = ve.find_twins(dummy)
    for t in twins:
        print(t)
