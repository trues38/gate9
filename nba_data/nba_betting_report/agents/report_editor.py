"""Report Editor: 모든 출력 → Daily_Report.md

Report Editor — Formatting & Presentation Layer

This module generates the final Daily_Report.md output.
This is a "sellable product" - the report structure is FIXED and stable.

Role:
    - Format all pipeline outputs into markdown
    - Present decisions and analysis in readable structure
    - Maintain consistent report template

PROHIBITED IN REPORT:
    - Win probability or win rate
    - Outcome predictions ("Team X will win")
    - Expected value (EV) calculations
    - Betting recommendations ("You should bet")
    - Performance metrics (ROI, profit/loss)
    - Statistical confidence intervals
    - Making new judgments not present in inputs
    - Recalculating any values
    - Reinterpreting patterns or decisions

ALLOWED IN REPORT:
    - Structural signal strength (edge_score)
    - Actionability classification (BET/MONITOR/PASS)
    - Structural-market relationship (line_comment)
    - Data quality metrics
    - Game counts and aggregations

DAILY_REPORT.MD TEMPLATE STRUCTURE (FIXED):

1. Executive Summary
   - Total games processed
   - Count of BET signals (NOT win predictions)
   - Count of high confidence actionable regimes

2. Betting Decisions
   - High Confidence: edge_score >= 70
   - Monitor: 30 <= edge_score < 50
   - Pass: edge_score < 30
   (Medium confidence BETs shown in High Confidence section)

3. Pattern Analysis
   - Structural profile descriptors (stub allowed in v0.1)
   - Historical pattern indicators (stub allowed in v0.1)

4. Risk Factors
   - Structural uncertainties
   - Data quality concerns
   (Generic risks allowed in v0.1)

5. Data Quality
   - Valid game count
   - Anomalies detected
"""

def generate(structural_output, pattern_output, decision_output):
    """
    입력: 모든 이전 에이전트 출력
    출력: Daily_Report.md (마크다운 문자열)

    ⚠️ This is pure formatting - no new calculations or judgments
    ⚠️ Report structure is FIXED - changes to internal logic should not affect template
    """
    game_contexts = structural_output.get("game_contexts", [])
    metadata = structural_output.get("metadata", {})
    game_patterns = pattern_output.get("game_patterns", [])
    betting_decisions = decision_output.get("betting_decisions", [])
    session_summary = decision_output.get("session_summary", {})

    # ========================================
    # SECTION 1: EXECUTIVE SUMMARY
    # ========================================
    # High-level metrics only - no predictions or probabilities
    report = f"""# NBA Daily Betting Report - {game_contexts[0]['date'] if game_contexts else 'N/A'}

## Executive Summary

- **Total Games Analyzed**: {metadata.get('total_games', 0)}
- **Bet Signals**: {session_summary.get('total_bet_signals', 0)}
- **High Confidence Bets**: {session_summary.get('high_confidence_count', 0)}

## Betting Decisions

"""

    # ========================================
    # SECTION 2: BETTING DECISIONS
    # ========================================
    # Actionability classifications - NOT outcome predictions
    # BET = actionable structural regime detected
    # MONITOR = weak signal, requires observation
    # PASS = insufficient structural signal

    # High Confidence subsection (edge_score >= 70, or medium BETs >= 50)
    high_conf = [d for d in betting_decisions if d["confidence"] == "high"]
    medium_conf = [d for d in betting_decisions if d["confidence"] == "medium" and d["action"] == "bet"]

    # Combine high + medium BETs in High Confidence section
    all_bets = high_conf + medium_conf

    if all_bets:
        report += "### High Confidence\n\n"
        for dec in all_bets:
            # Format: Game ID - ACTION side
            # Reasoning: structural basis for classification
            # Line: structural-market relationship (NOT efficiency judgment)
            # Risks: structural uncertainties
            report += f"**Game {dec['game_id']}** - {dec['action'].upper()} {dec['side']}\n"
            report += f"- Reasoning: {dec['reasoning']}\n"
            report += f"- Line: {dec['line_comment']}\n"
            report += f"- Risks: {', '.join(dec['risk_notes'])}\n\n"
    else:
        report += "### High Confidence\n\nNone\n\n"

    # Monitor subsection (30 <= edge_score < 50)
    monitor = [d for d in betting_decisions if d["action"] == "monitor"]
    report += "### Monitor\n\n"
    if monitor:
        for dec in monitor:
            # Weak signals - observable but not actionable
            report += f"**Game {dec['game_id']}** - {dec['reasoning']}\n"
            report += f"- Line: {dec['line_comment']}\n\n"
    else:
        report += "None\n\n"

    # Pass subsection (edge_score < 30)
    passed = [d for d in betting_decisions if d["action"] == "pass"]
    report += "### Pass\n\n"
    if passed:
        for dec in passed:
            # Insufficient structural signal
            report += f"**Game {dec['game_id']}** - {dec['reasoning']}\n"
            report += f"- Line: {dec['line_comment']}\n\n"
    else:
        report += "None\n\n"

    # ========================================
    # SECTION 3: PATTERN ANALYSIS
    # ========================================
    # Structural descriptors (stub allowed in v0.1)
    # These describe game-intrinsic characteristics
    # NOT predictive metrics
    report += "## Pattern Analysis\n\n"
    for pattern in game_patterns:
        report += f"**Game {pattern['game_id']}**\n"
        report += f"- Pace: {pattern['structural_profile']['pace']}\n"
        report += f"- Trend: {pattern['historical_pattern']['trend']}\n"
        report += f"- Form: {pattern['historical_pattern']['recent_form']}\n\n"

    # ========================================
    # SECTION 4: RISK FACTORS
    # ========================================
    # Structural uncertainties and data quality concerns
    # NOT outcome-based risks
    report += "## Risk Factors\n\n"
    for risk in session_summary.get("major_risks", []):
        report += f"- {risk}\n"

    # ========================================
    # SECTION 5: DATA QUALITY
    # ========================================
    # Input validation metrics
    report += "\n## Data Quality\n\n"
    report += f"- Valid Games: {metadata.get('valid_games', 0)}/{metadata.get('total_games', 0)}\n"
    if metadata.get("anomalies"):
        report += "- Anomalies:\n"
        for anomaly in metadata["anomalies"]:
            report += f"  - {anomaly}\n"

    return report
