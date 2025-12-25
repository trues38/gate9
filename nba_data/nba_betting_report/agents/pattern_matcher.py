"""Pattern Matcher: game_contexts → structural_profile + historical_pattern

edge_score v0.1 — Market-Independent Structural Density Score

This module calculates edge_score WITHOUT using any market data.
edge_score is derived SOLELY from game-intrinsic quantitative signals.

Version: v0.1 (baseline)
Philosophy: Reproducibility > Accuracy
"""

def _calculate_edge_score_v01(box_stats, scores):
    """
    edge_score v0.1 calculation engine

    Inputs:
        - box_stats: dict with derived metrics
        - scores: dict with home/away final scores

    Output:
        - edge_score: float (0-100)

    Signals used (market-independent):
        1. Shooting Efficiency (40% weight)
        2. Rebounding Dominance (25% weight)
        3. Pace Proxy (15% weight)
        4. Score Margin (20% weight)

    ⚠️ This is v0.1 - deterministic baseline, NOT optimized for accuracy.
    """
    # PLUS_MINUS intentionally excluded from edge_score (noise-prone)

    # Extract data (restricted to approved keys only)
    home_efg = box_stats.get("home_efg_pct", 0.50)
    away_efg = box_stats.get("away_efg_pct", 0.50)
    reb_diff = box_stats.get("reb_diff", 0)
    pace_est = box_stats.get("pace_est", 100)
    score_margin = box_stats.get("score_margin", 0)

    # Signal 1: Shooting Efficiency (eFG%)
    efg_diff = abs(home_efg - away_efg)

    # Normalize: 0.0-0.15 diff → 0-100 scale
    efficiency_signal = min(100, (efg_diff / 0.15) * 100)

    # Signal 2: Rebounding Dominance
    # Normalize: 0-20 reb diff → 0-100 scale
    rebounding_signal = min(100, (abs(reb_diff) / 20) * 100)

    # Signal 3: Pace Proxy
    # League average: ~100 possessions, high pace: >110, low pace: <90
    pace_deviation = abs(pace_est - 100)

    # Normalize: 0-20 deviation → 0-100 scale
    pace_signal = min(100, (pace_deviation / 20) * 100)

    # Signal 4: Score Margin (game decisiveness)
    # Normalize: 0-30 margin → 0-100 scale
    margin_signal = min(100, (score_margin / 30) * 100)

    # Weighted combination
    edge_score = (
        efficiency_signal * 0.40 +
        rebounding_signal * 0.25 +
        pace_signal * 0.15 +
        margin_signal * 0.20
    )

    # Round to integer
    return round(edge_score, 0)


def analyze(structural_output):
    """
    입력: game_contexts
    출력: game_patterns (structural_profile + historical_pattern + edge_score)

    ⚠️ edge_score is CALCULATED here, NOT read from input
    """
    game_contexts = structural_output.get("game_contexts", [])
    game_patterns = []

    for ctx in game_contexts:
        # ⚠️ CRITICAL: edge_score is calculated, NOT read from input
        box_stats = ctx.get("box_stats", {})
        scores = ctx.get("scores", {})

        # Calculate edge_score using market-independent signals
        edge_score = _calculate_edge_score_v01(box_stats, scores)

        # Stub: 실제 패턴 계산 없음
        pattern = {
            "game_id": ctx["game_id"],
            "edge_score": edge_score,  # NOW CALCULATED, not from input
            "market_line": ctx.get("market_line", 0),
            "structural_profile": {
                "pace": "normal",  # stub
                "scoring_distribution": "balanced",  # stub
                "efficiency": "average",  # stub
                "volatility": "low"  # stub
            },
            "historical_pattern": {
                "trend": "stable",  # stub
                "recent_form": "neutral",  # stub
                "streak": "none",  # stub
                "deviation": "minimal"  # stub
            }
        }
        game_patterns.append(pattern)

    return {"game_patterns": game_patterns}
