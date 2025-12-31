#!/usr/bin/env python3
"""
xG-Based Betting Analysis Engine

Analyzes xG data to identify betting opportunities:
- xG overperformance/underperformance (mean reversion)
- Recent xG form and trends
- Home/away xG patterns
- Value bet opportunities
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"


def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(str(DB_PATH))


def calculate_xg_performance(conn, league, min_matches=5):
    """
    Calculate xG over/under performance for all teams

    Returns teams that are scoring significantly more/less than their xG
    This indicates potential regression to the mean
    """
    query = """
    SELECT
        CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
        COUNT(*) as matches,
        SUM(CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END) as actual_goals,
        SUM(ms.xg) as expected_goals,
        SUM(CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END) - SUM(ms.xg) as xg_diff,
        ROUND(AVG(ms.xg), 2) as avg_xg,
        ROUND(AVG(CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END), 2) as avg_goals
    FROM matches m
    JOIN match_stats ms ON m.match_id = ms.match_id
    WHERE m.league = ?
    AND ms.xg IS NOT NULL
    AND m.date >= date('now', '-90 days')
    GROUP BY team
    HAVING COUNT(*) >= ?
    ORDER BY xg_diff DESC
    """

    cursor = conn.execute(query, (league, min_matches))
    teams = []

    for row in cursor.fetchall():
        team, matches, actual, expected, diff, avg_xg, avg_goals = row

        # Calculate performance percentage
        perf_pct = ((actual / expected) - 1) * 100 if expected > 0 else 0

        teams.append({
            'team': team,
            'matches': matches,
            'actual_goals': actual,
            'expected_goals': round(expected, 2),
            'xg_diff': round(diff, 2),
            'performance_pct': round(perf_pct, 1),
            'avg_xg': avg_xg,
            'avg_goals': avg_goals,
            'status': 'overperforming' if diff > 2 else 'underperforming' if diff < -2 else 'normal'
        })

    return teams


def calculate_recent_form(conn, league, last_n_matches=5):
    """
    Calculate recent xG form (last N matches)
    """
    query = """
    WITH recent_matches AS (
        SELECT
            CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
            m.date,
            ms.xg,
            ms.xga,
            CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END as goals_scored,
            CASE WHEN ms.is_home = 1 THEN m.away_score ELSE m.home_score END as goals_conceded,
            ROW_NUMBER() OVER (
                PARTITION BY CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END
                ORDER BY m.date DESC
            ) as rn
        FROM matches m
        JOIN match_stats ms ON m.match_id = ms.match_id
        WHERE m.league = ?
        AND ms.xg IS NOT NULL
    )
    SELECT
        team,
        COUNT(*) as matches,
        ROUND(AVG(xg), 2) as avg_xg,
        ROUND(AVG(xga), 2) as avg_xga,
        ROUND(AVG(goals_scored), 2) as avg_goals,
        ROUND(AVG(goals_conceded), 2) as avg_conceded
    FROM recent_matches
    WHERE rn <= ?
    GROUP BY team
    HAVING COUNT(*) = ?
    ORDER BY avg_xg DESC
    """

    cursor = conn.execute(query, (league, last_n_matches, last_n_matches))
    teams = []

    for row in cursor.fetchall():
        team, matches, avg_xg, avg_xga, avg_goals, avg_conceded = row

        # Handle None values
        avg_xg = avg_xg if avg_xg is not None else 0.0
        avg_xga = avg_xga if avg_xga is not None else 0.0

        teams.append({
            'team': team,
            'matches': matches,
            'avg_xg': avg_xg,
            'avg_xga': avg_xga,
            'avg_goals': avg_goals,
            'avg_conceded': avg_conceded,
            'xg_diff': round(avg_xg - avg_xga, 2)
        })

    return teams


def calculate_home_away_split(conn, league, min_matches=3):
    """
    Calculate home vs away xG performance
    Identify teams with significant home/away differences
    """
    query = """
    SELECT
        CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
        ms.is_home,
        COUNT(*) as matches,
        ROUND(AVG(ms.xg), 2) as avg_xg,
        ROUND(AVG(ms.xga), 2) as avg_xga
    FROM matches m
    JOIN match_stats ms ON m.match_id = ms.match_id
    WHERE m.league = ?
    AND ms.xg IS NOT NULL
    AND m.date >= date('now', '-90 days')
    GROUP BY team, ms.is_home
    HAVING COUNT(*) >= ?
    """

    cursor = conn.execute(query, (league, min_matches))

    # Organize by team
    teams_data = defaultdict(dict)
    for row in cursor.fetchall():
        team, is_home, matches, avg_xg, avg_xga = row
        venue = 'home' if is_home == 1 else 'away'
        teams_data[team][venue] = {
            'matches': matches,
            'avg_xg': avg_xg,
            'avg_xga': avg_xga
        }

    # Calculate differences
    results = []
    for team, data in teams_data.items():
        if 'home' in data and 'away' in data:
            home_xg = data['home']['avg_xg']
            away_xg = data['away']['avg_xg']
            diff = home_xg - away_xg

            results.append({
                'team': team,
                'home_xg': home_xg,
                'away_xg': away_xg,
                'home_away_diff': round(diff, 2),
                'home_advantage': diff > 0.5,
                'away_advantage': diff < -0.5
            })

    # Sort by absolute difference
    results.sort(key=lambda x: abs(x['home_away_diff']), reverse=True)
    return results


def find_value_bets(conn, league):
    """
    Find potential value bets based on xG analysis

    Criteria:
    1. Team is significantly underperforming xG (expected to score more)
    2. Team has strong recent xG form
    3. Opponent has weak defensive xG
    """
    # Get performance data
    performance = calculate_xg_performance(conn, league)
    recent_form = calculate_recent_form(conn, league)

    # Create lookup dictionaries
    perf_dict = {t['team']: t for t in performance}
    form_dict = {t['team']: t for t in recent_form}

    value_bets = []

    for team in performance:
        team_name = team['team']

        # Skip if not in recent form
        if team_name not in form_dict:
            continue

        form = form_dict[team_name]

        # Criteria for value bet
        underperforming = team['xg_diff'] < -2  # Scoring 2+ goals less than xG
        strong_xg = form['avg_xg'] > 1.3  # Creating good chances

        if underperforming and strong_xg:
            value_bets.append({
                'team': team_name,
                'xg_diff': team['xg_diff'],
                'recent_avg_xg': form['avg_xg'],
                'recent_avg_goals': form['avg_goals'],
                'performance_pct': team['performance_pct'],
                'recommendation': 'BACK TO SCORE' if team['xg_diff'] < -3 else 'MONITOR'
            })

    value_bets.sort(key=lambda x: x['xg_diff'])
    return value_bets


def generate_league_analysis(league):
    """Generate complete xG analysis for a league"""
    conn = get_db_connection()

    analysis = {
        'league': league,
        'generated_at': datetime.now().isoformat(),
        'performance': calculate_xg_performance(conn, league),
        'recent_form': calculate_recent_form(conn, league),
        'home_away': calculate_home_away_split(conn, league),
        'value_bets': find_value_bets(conn, league)
    }

    conn.close()
    return analysis


def generate_all_leagues_analysis():
    """Generate analysis for all leagues"""
    leagues = ['EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1']

    all_analysis = {}
    for league in leagues:
        print(f"Analyzing {league}...")
        all_analysis[league] = generate_league_analysis(league)

    return all_analysis


def save_analysis(analysis, output_path):
    """Save analysis to JSON file"""
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"✅ Analysis saved to {output_path}")


if __name__ == "__main__":
    print("="*60)
    print("xG Betting Analysis Engine")
    print("="*60)

    # Generate analysis
    analysis = generate_all_leagues_analysis()

    # Save to file
    output_dir = BASE_DIR / "analysis" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"xg_analysis_{timestamp}.json"

    save_analysis(analysis, output_path)

    print("\n" + "="*60)
    print("Analysis Complete")
    print("="*60)
