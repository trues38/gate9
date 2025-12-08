from typing import Dict
import json

def calculate_unified_risk(macro_state: Dict, pattern_id: str, meta_rag_warning: Dict) -> Dict:
    """
    Calculates the Unified Risk Score (0-100).
    Components:
    - Macro Regime Risk: 35%
    - Pattern-Driven Risk: 25%
    - Meta-RAG Weighted Risk: 25%
    - Momentum Trend Risk: 15%
    """
    
    # 1. Macro Regime Risk (35%)
    regime = macro_state.get('regime', 'NEUTRAL')
    macro_score = 40 # Default Neutral
    if regime == "LIQUIDITY_CRISIS": macro_score = 100
    elif regime == "STAGFLATION": macro_score = 80
    elif regime == "INFLATION_FEAR": macro_score = 60
    elif regime == "GROWTH_GOLDILOCKS": macro_score = 20
    
    # 2. Pattern Risk (25%)
    pattern_score = 20 # Default Low
    if pattern_id in ["P-005", "P-005A", "P-008", "P-008B", "P-028", "P-047"]:
        pattern_score = 90
    elif pattern_id in ["P-001", "P-001A", "P-003"]:
        pattern_score = 50
        
    # 3. Meta-RAG Risk (25%)
    meta_score = 0
    if meta_rag_warning:
        try:
            reason_json = json.loads(meta_rag_warning.get('fail_reason', '{}'))
            risk_weight = reason_json.get('risk_weight', 1.0)
            meta_score = min(risk_weight * 20, 100) # 1.0 -> 20, 5.0 -> 100
            # Boost if HARD override
            if meta_rag_warning.get('override_level') == 'HARD':
                meta_score = max(meta_score, 80)
        except:
            meta_score = 20
            
    # 4. Momentum Risk (15%)
    # High VIX = High Risk
    vix = macro_state.get('VIX', {}).get('value', 20.0)
    momentum_score = 20
    if vix > 30: momentum_score = 100
    elif vix > 20: momentum_score = 60
    
    # Weighted Sum
    total_score = (macro_score * 0.35) + \
                  (pattern_score * 0.25) + \
                  (meta_score * 0.25) + \
                  (momentum_score * 0.15)
                  
    # Interpretation
    label = "Low Risk"
    action = "Normal Operations"
    if total_score >= 70:
        label = "High Risk"
        action = "Reduce Position or Hold Cash"
    elif total_score >= 40:
        label = "Moderate Risk"
        action = "Trade Lightly"
        
    return {
        "score": round(total_score, 1),
        "label": label,
        "action": action,
        "details": {
            "macro": macro_score,
            "pattern": pattern_score,
            "meta_rag": meta_score,
            "momentum": momentum_score
        }
    }
