# Regime Weight Table
# Derived from RData Analysis (38,000 games)
# Impact represents the change in Favorite Win Rate.
# Negative means Favorite loses more often (Upset Likely).
# Positive means Favorite wins more often (Upset Unlikely).

REGIME_WEIGHTS = {
    # Calendar Effects
    "calendar_june": -0.084, # The "June Gloom" (Finals Chaos)
    "calendar_may": +0.021,  # The "May Might" (Playoff Order)
    
    # Structural Regimes
    "nemesis": -0.045,       # "History doesn't lie" (Score Gap < -5)
    "momentum_trap": -0.034, # "The Trap" (Fav Cold / Dog Hot)
    
    # Combinations (Clusters)
    # These are additive triggers? Or exclusive?
    # For now, we use them as additive risk factors.
    "god_tier_upset": -0.150 # Fatigue + Momentum + Nemesis (54% Dog Win Rate -> Massive Shift)
}

def get_regime_impact(matches_regime: str) -> float:
    return REGIME_WEIGHTS.get(matches_regime, 0.0)
