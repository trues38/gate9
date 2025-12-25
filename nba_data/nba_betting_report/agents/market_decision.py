"""Market & Decision: game_patterns → betting_decisions

Decision Layer — Actionability Classifier (NOT Outcome Predictor)

Role:
    - Consumes edge_score from Pattern Matcher
    - Classifies actionability based on structural signal strength
    - Compares edge_score with market_line to assess structural-market alignment

This layer is where market_line is used FOR THE FIRST TIME.

PROHIBITED:
    - Recalculating edge_score
    - Estimating win probability
    - Predicting game outcomes
    - Making betting recommendations
    - Statistical inference beyond classification

ALLOWED:
    - Classifying structural actionability (BET/MONITOR/PASS)
    - Describing structural-market relationship (line_comment)
    - Listing structural risks
"""

def analyze(pattern_output):
    """
    입력: game_patterns (including edge_score from Pattern Matcher)
    출력: betting_decisions, session_summary

    ⚠️ edge_score is CONSUMED, never recalculated
    ⚠️ This is actionability classification, NOT prediction
    """
    game_patterns = pattern_output.get("game_patterns", [])
    betting_decisions = []

    for pattern in game_patterns:
        # ⚠️ CRITICAL: edge_score is READ ONLY, never modified or recalculated
        edge_score = pattern.get("edge_score", 0)
        market_line = pattern.get("market_line", 0)

        # Actionability Classification Rules (v0.1 baseline thresholds)
        # These thresholds define SIGNAL STRENGTH, not win probability

        if edge_score >= 70:
            # Strong structural signal alignment
            action = "bet"
            confidence = "high"
            reasoning = f"Strong edge detected (score: {edge_score})"

        elif edge_score >= 50:
            # Moderate structural signal density
            action = "bet"
            confidence = "medium"
            reasoning = f"Moderate edge detected (score: {edge_score})"

        elif edge_score >= 30:
            # Weak signal, observable but not actionable
            action = "monitor"
            confidence = "low"
            reasoning = f"Weak signal, monitoring required (score: {edge_score})"

        else:
            # Insufficient structural signal
            action = "pass"
            confidence = "low"
            reasoning = f"Insufficient edge (score: {edge_score})"

        # Structural-Market Relationship Heuristic (v0.1 stub logic)
        # This describes the relationship between structural signals and market line
        # NOT a value judgment or efficiency claim
        line_abs = abs(market_line)

        if edge_score >= 70 and line_abs < 3:
            # Strong signal but tight market line
            line_comment = "라인이 과하다"  # Line appears excessive relative to structure

        elif edge_score >= 70 and line_abs > 6:
            # Strong signal with wide market line
            line_comment = "라인이 보수적이다"  # Line appears conservative relative to structure

        elif edge_score < 30 and line_abs > 6:
            # Weak signal with wide market line
            line_comment = "라인이 과하다"  # Line appears excessive given weak structure

        else:
            # Structural-market alignment appears reasonable
            line_comment = "라인이 무난하다"  # Line aligns with structural signals

        decision = {
            "game_id": pattern["game_id"],
            "action": action,
            "side": "home",  # v0.1: fixed to home (intentional stub)
            "confidence": confidence,
            "reasoning": reasoning,
            "line_comment": line_comment,
            "risk_notes": ["Low sample size", "Potential lineup change"]  # v0.1: stub
        }
        betting_decisions.append(decision)

    # Session summary aggregation
    session_summary = {
        "total_bet_signals": len([d for d in betting_decisions if d["action"] == "bet"]),
        "high_confidence_count": len([d for d in betting_decisions if d["confidence"] == "high"]),
        "major_risks": ["Market volatility", "Injury reports pending"]  # v0.1: stub
    }

    return {
        "betting_decisions": betting_decisions,
        "session_summary": session_summary
    }
