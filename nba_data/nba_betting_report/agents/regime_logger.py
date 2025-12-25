"""Regime Logger — Passive Observation Accumulator

This module accumulates raw observations for future regime identification.

PURPOSE:
    - Log edge_score, market_line, and action decisions
    - Accumulate data WITHOUT interpreting patterns
    - Provide raw material for post-hoc regime discovery

NOT USED IN v0.1:
    - This data is NOT used for current decisions
    - No regime detection is performed here
    - No pattern matching or classification

FUTURE USE:
    - After N observations (e.g., 100+ games)
    - Analyze repeated combinations of (edge_score, market_line, action)
    - Identify and name emergent regimes post-hoc
    - Validate regime consistency over time

⚠️ This is a PASSIVE logger - it does not influence pipeline behavior
"""

import json
import os
from datetime import datetime


def log_observations(game_patterns, betting_decisions, game_contexts):
    """
    Log raw observations to regime_log.jsonl

    Inputs:
        - game_patterns: list of patterns from Pattern Matcher
        - betting_decisions: list of decisions from Decision Layer
        - game_contexts: list of contexts from Structural Analyst

    Output:
        - Appends observations to regime_observations.jsonl

    ⚠️ This function does NOT:
        - Detect regimes
        - Analyze patterns
        - Make decisions
        - Influence pipeline output

    This is pure data accumulation for future analysis.
    """

    log_file = "regime_observations.jsonl"

    # Merge data from all sources
    observations = []

    for i, pattern in enumerate(game_patterns):
        # Find corresponding decision and context
        game_id = pattern.get("game_id")

        decision = next((d for d in betting_decisions if d["game_id"] == game_id), None)
        context = next((c for c in game_contexts if c["game_id"] == game_id), None)

        if not decision or not context:
            continue  # Skip incomplete data

        # Create observation record
        observation = {
            # Identifiers
            "date": context.get("date", ""),
            "game_id": game_id,
            "timestamp": datetime.now().isoformat(),

            # Core signals (market-independent)
            "edge_score": pattern.get("edge_score", 0),

            # Market data (Decision Layer input)
            "market_line": pattern.get("market_line", 0),

            # Decision output
            "action": decision.get("action", ""),
            "confidence": decision.get("confidence", ""),

            # Structural profile (for future analysis, stub in v0.1)
            "pace": pattern.get("structural_profile", {}).get("pace", ""),
            "trend": pattern.get("historical_pattern", {}).get("trend", ""),

            # Metadata
            "pipeline_version": "v0.1"
        }

        observations.append(observation)

    # Append to log file (JSON Lines format)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            for obs in observations:
                f.write(json.dumps(obs, ensure_ascii=False) + "\n")

        return {
            "logged_count": len(observations),
            "log_file": log_file,
            "status": "success"
        }

    except Exception as e:
        return {
            "logged_count": 0,
            "log_file": log_file,
            "status": "error",
            "error": str(e)
        }


def get_log_stats():
    """
    Get statistics about accumulated observations

    Returns:
        - total_observations: count of logged observations
        - date_range: first and last observation dates
        - action_distribution: count of each action type

    ⚠️ This is for monitoring only, NOT for decision-making
    """
    log_file = "regime_observations.jsonl"

    if not os.path.exists(log_file):
        return {
            "total_observations": 0,
            "message": "No observations logged yet"
        }

    try:
        observations = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                observations.append(json.loads(line))

        if not observations:
            return {"total_observations": 0}

        # Basic statistics
        action_counts = {}
        for obs in observations:
            action = obs.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        dates = [obs.get("date", "") for obs in observations if obs.get("date")]

        return {
            "total_observations": len(observations),
            "date_range": {
                "first": min(dates) if dates else None,
                "last": max(dates) if dates else None
            },
            "action_distribution": action_counts,
            "status": "success"
        }

    except Exception as e:
        return {
            "total_observations": 0,
            "status": "error",
            "error": str(e)
        }
