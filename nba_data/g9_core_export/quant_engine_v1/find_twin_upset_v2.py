
import json
import os
import numpy as np
from datetime import datetime

# Config
ENRICHED_LIBRARY = "/Users/js/g9/nba_data/quant_engine/upset_library_enriched.json"

# Weights
WEIGHT_NARRATIVE = 0.7
WEIGHT_CONTEXT = 0.3

class TwinEngineV2:
    def __init__(self):
        self.library = self._load_library()
        
    def _load_library(self):
        if not os.path.exists(ENRICHED_LIBRARY):
            # Fallback to tagged if enriched missing (Graceful degradation)
            fallback = "/Users/js/g9/nba_data/quant_engine/upset_library_tagged.json"
            if os.path.exists(fallback):
                print("Warning: Enriched library not found. Using Tagged library (No Context Weights).")
                with open(fallback, 'r') as f:
                    return json.load(f)
            return []
        
        with open(ENRICHED_LIBRARY, 'r') as f:
            return json.load(f)

    def find_twins(self, current_game_context, narrative_vector):
        """
        Find twins based on Weighted Score (Narrative + Context).
        current_game_context: { "rest_days": 0, "streak": -3, "location": "AWAY" }
        """
        # 1. Similarity Search (Mock Vector Dot Product)
        # In real impl, we'd use ChromaDB or numpy dot product with `narrative_vector`
        # Here we simulate the Vector matching by random scores or using the Mock Classifications
        
        scored_candidates = []
        
        for game in self.library:
            # A. Narrative Similarity (Placeholder logic)
            # If current game has similar 'Cause', give high score
            # In real vector search, this comes from the Embedding Distance
            narr_score = np.random.uniform(0.7, 0.99) # Placeholder
            
            # B. Context Score (The Bonus)
            ctx_score = 0.0
            game_ctx = game.get('context', {})
            
            # Bonus 1: Rest Days Logic (If both are B2B or both Rested)
            cur_rest = current_game_context.get('rest_days')
            hist_rest = game_ctx.get('rest_days')
            if cur_rest is not None and hist_rest is not None:
                if cur_rest == hist_rest:
                    ctx_score += 0.5
                elif cur_rest == 0 and hist_rest == 0: # Both B2B = Huge Bonus
                    ctx_score += 0.8
            
            # Bonus 2: Location
            hist_loc = game_ctx.get('location')
            if current_game_context.get('location') and hist_loc:
                if current_game_context.get('location') == hist_loc:
                    ctx_score += 0.2
                
            # Normalize Context Score (0 to 1)
            ctx_score = min(ctx_score, 1.0)
            
            # Handling Missing Context (Historical Data often has nulls)
            if hist_rest is None and hist_loc is None:
                # If no context available, rely 100% on Narrative (with slight penalty)
                final_score = narr_score * 0.9
            else:
                # Standard Weighting
                final_score = (narr_score * WEIGHT_NARRATIVE) + (ctx_score * WEIGHT_CONTEXT)
            
            scored_candidates.append({
                "game_id": game['game_id'],
                "matchup": f"{game['underdog']} def. {game['favorite']}",
                "date": game['date'],
                "narrative_score": round(narr_score, 3),
                "context_score": round(ctx_score, 3),
                "final_score": round(final_score, 3),
                "cause": game.get('cause_classification', {}).get('primary_cause'),
                "context_match": f"Rest:{hist_rest}, Loc:{hist_loc}"
            })
            
        # Sort and Return Top 3 (Strict Threshold)
        scored_candidates.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Threshold: Lowered to 0.60 to ensure at least "Quiet" detection
        # Since average high narr match is ~0.8 * 0.9 = 0.72.
        
        filtered = [x for x in scored_candidates if x['final_score'] >= 0.60]
        
        return filtered[:1] if filtered else []

if __name__ == "__main__":
    # Test Run
    engine = TwinEngineV2()
    
    # Mock Current Game: Lakers (Fav) on B2B, Away, Losing Streak 2
    mock_context = {"rest_days": 0, "streak": -2, "location": "AWAY"} 
    mock_vector = [] # Placeholder
    
    twins = engine.find_twins(mock_context, mock_vector)
    
    print("=== Found Twins (Weighted) ===")
    print(json.dumps(twins, indent=2))
