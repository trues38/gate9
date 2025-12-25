
# Layer 15: Composite Score
# Weighted Sum of all layers

def calculate_composite(layers_dict):
    # Define Weights
    weights = {
        "momentum": 0.15,
        "pace": 0.05,
        "star_form": 0.15,
        "matchup": 0.10,
        "injury": 0.15, # Negative impact usually
        "schedule": 0.10, # Negative
        "clutch": 0.05,
        "defense": 0.10,
        "variance": 0.05,
        "psych": 0.10
    }
    
    # Normalize inputs driven by Orchestrator?
    # Or just sum raw.
    # Assuming normalized 0-100 or -10 to +10.
    
    # For now, just a direct linear combination.
    visited_score = 0
    
    # Momentum (High good)
    visited_score += layers_dict.get('momentum', 0) * weights['momentum']
    
    # Star Form (High good)
    visited_score += layers_dict.get('star_form', 0) * weights['star_form']
    
    # ...
    
    return round(visited_score, 2)
