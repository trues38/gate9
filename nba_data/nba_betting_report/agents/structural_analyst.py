"""Structural Analyst: 원시 JSON → game_contexts

Structural Analyst — Data Validation & Normalization Layer

Role:
    - Validate raw input data
    - Normalize game structure
    - Detect data quality issues
    - Pass normalized data to Pattern Matcher

PROHIBITED:
    - Calculating edge_score (Pattern Matcher's job)
    - Using market_line for analysis (Decision Layer's job)
    - Pattern interpretation
    - Making betting judgments

ALLOWED:
    - Data validation
    - Structural normalization
    - Completeness checking
    - Anomaly detection
"""

def _safe_divide(num, denom, default=0.0):
    """Safe division with zero handling"""
    return num / denom if denom != 0 else default


def _parse_espn_team_stats(team_stats):
    """Extract raw fields from ESPN Boxscore format"""
    return {
        "PTS": team_stats.get("points", 0),
        "FGM": team_stats.get("fieldGoalsMade", 0),
        "FGA": team_stats.get("fieldGoalsAttempted", 0),
        "FG3M": team_stats.get("threePointFieldGoalsMade", 0),
        "FG3A": team_stats.get("threePointFieldGoalsAttempted", 0),
        "FTM": team_stats.get("freeThrowsMade", 0),
        "FTA": team_stats.get("freeThrowsAttempted", 0),
        "OREB": team_stats.get("offensiveRebounds", 0),
        "DREB": team_stats.get("defensiveRebounds", 0),
        "REB": team_stats.get("totalRebounds", 0),
        "TOV": team_stats.get("totalTurnovers", 0),
        "PLUSMINUS": team_stats.get("plusMinus", 0)
    }


def _derive_metrics(home_raw, away_raw):
    """Calculate derived metrics from raw stats"""

    # Shooting percentages
    home_fg_pct = _safe_divide(home_raw["FGM"], home_raw["FGA"])
    away_fg_pct = _safe_divide(away_raw["FGM"], away_raw["FGA"])

    home_fg3_pct = _safe_divide(home_raw["FG3M"], home_raw["FG3A"])
    away_fg3_pct = _safe_divide(away_raw["FG3M"], away_raw["FG3A"])

    home_ft_pct = _safe_divide(home_raw["FTM"], home_raw["FTA"])
    away_ft_pct = _safe_divide(away_raw["FTM"], away_raw["FTA"])

    # Effective FG%
    home_efg = _safe_divide(home_raw["FGM"] + 0.5 * home_raw["FG3M"], home_raw["FGA"])
    away_efg = _safe_divide(away_raw["FGM"] + 0.5 * away_raw["FG3M"], away_raw["FGA"])

    # NOTE:
    # possessions and pace are ESTIMATES derived from boxscore data
    # ESPN does NOT provide official possessions or pace fields
    # These metrics are used for structural comparison only

    # Possessions estimate
    home_poss = home_raw["FGA"] + home_raw["TOV"] + 0.44 * home_raw["FTA"] - home_raw["OREB"]
    away_poss = away_raw["FGA"] + away_raw["TOV"] + 0.44 * away_raw["FTA"] - away_raw["OREB"]

    # Pace estimate (assumes 48 mins, 5 players)
    total_poss = home_poss + away_poss
    pace_est = _safe_divide(48 * total_poss, 2 * 48)

    # Rebounding metrics
    reb_diff = home_raw["REB"] - away_raw["REB"]
    home_oreb_rate = _safe_divide(home_raw["OREB"], home_raw["OREB"] + away_raw["DREB"])
    away_oreb_rate = _safe_divide(away_raw["OREB"], away_raw["OREB"] + home_raw["DREB"])

    # Score margin
    score_margin = abs(home_raw["PTS"] - away_raw["PTS"])

    return {
        "home_fg_pct": home_fg_pct,
        "away_fg_pct": away_fg_pct,
        "home_3p_pct": home_fg3_pct,
        "away_3p_pct": away_fg3_pct,
        "home_ft_pct": home_ft_pct,
        "away_ft_pct": away_ft_pct,
        "home_efg_pct": home_efg,
        "away_efg_pct": away_efg,
        "home_rebounds": home_raw["REB"],
        "away_rebounds": away_raw["REB"],
        "reb_diff": reb_diff,
        "home_oreb_rate": home_oreb_rate,
        "away_oreb_rate": away_oreb_rate,
        "pace_est": pace_est,
        "score_margin": score_margin
    }


def analyze(raw_data):
    """
    입력: ESPN Boxscore JSON (game data without edge_score)
    출력: game_contexts, metadata

    ⚠️ edge_score should NOT be in raw input
    ⚠️ market_line is passed through without analysis
    """
    games = raw_data.get("games", [])

    game_contexts = []
    anomalies = []

    for game in games:
        # Extract raw team stats
        home_stats = game.get("home_stats", {})
        away_stats = game.get("away_stats", {})

        # Parse ESPN format
        home_raw = _parse_espn_team_stats(home_stats)
        away_raw = _parse_espn_team_stats(away_stats)

        # Derive calculated metrics
        box_stats = _derive_metrics(home_raw, away_raw)

        # Data completeness validation
        has_required_fields = (
            game.get("game_id") and
            game.get("teams") and
            home_raw["PTS"] > 0 and
            away_raw["PTS"] > 0
        )
        completeness = "complete" if has_required_fields else "partial"

        # Normalized game context structure
        context = {
            "game_id": game.get("game_id", "unknown"),
            "date": game.get("date", ""),
            "teams": game.get("teams", {}),
            "scores": {"home": home_raw["PTS"], "away": away_raw["PTS"]},
            "box_stats": box_stats,
            "market_line": game.get("market_line", 0),
            "completeness": completeness
        }
        game_contexts.append(context)

        # Anomaly detection
        if completeness == "partial":
            anomalies.append(f"Game {context['game_id']}: missing required fields")

    # Data quality metadata
    metadata = {
        "total_games": len(games),
        "valid_games": len([g for g in game_contexts if g["completeness"] == "complete"]),
        "anomalies": anomalies
    }

    return {
        "game_contexts": game_contexts,
        "metadata": metadata
    }
