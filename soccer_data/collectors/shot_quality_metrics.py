#!/usr/bin/env python3
"""
Shot Quality Metrics Generator

Generates xG-alternative metrics from existing shot statistics.
Uses data already available in football-data.co.uk CSV files.
"""

import sqlite3
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"


def calculate_shot_quality_metrics():
    """
    Calculate shot quality metrics for all matches

    Metrics:
    - shot_quality: shots_on_target / total_shots (accuracy)
    - conversion_rate: goals / shots_on_target (efficiency)
    - shot_efficiency: goals / total_shots (overall)
    - shot_volume_index: total_shots / league_avg_shots (volume)
    """

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Add new columns if they don't exist
        for col in ['shot_quality', 'conversion_rate', 'shot_efficiency', 'shot_volume_index']:
            try:
                cursor.execute(f'ALTER TABLE match_stats ADD COLUMN {col} REAL')
                logger.info(f"Added column: {col}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Calculate league averages for shot volume index
        cursor.execute('''
            SELECT
                m.league,
                AVG(ms.shots) as avg_shots
            FROM matches m
            JOIN match_stats ms ON m.match_id = ms.match_id
            WHERE ms.shots > 0
            GROUP BY m.league
        ''')

        league_averages = {row[0]: row[1] for row in cursor.fetchall()}
        logger.info(f"League shot averages: {league_averages}")

        # Calculate metrics for each match_stats row
        cursor.execute('''
            SELECT
                ms.match_id,
                ms.is_home,
                CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END as goals,
                ms.shots,
                ms.shots_on_target,
                m.league
            FROM match_stats ms
            JOIN matches m ON ms.match_id = m.match_id
            WHERE ms.shots > 0
        ''')

        updates = []
        for row in cursor.fetchall():
            match_id, is_home, goals, shots, sot, league = row

            # Shot Quality (0-1, higher = better accuracy)
            shot_quality = round(sot / shots, 3) if shots > 0 else 0

            # Conversion Rate (0-1, higher = better finishing)
            conversion_rate = round(goals / sot, 3) if sot > 0 else 0

            # Shot Efficiency (0-1, overall effectiveness)
            shot_efficiency = round(goals / shots, 3) if shots > 0 else 0

            # Shot Volume Index (relative to league average)
            league_avg = league_averages.get(league, 12.0)
            shot_volume_index = round(shots / league_avg, 3)

            updates.append((
                shot_quality,
                conversion_rate,
                shot_efficiency,
                shot_volume_index,
                match_id,
                is_home
            ))

        # Batch update
        cursor.executemany('''
            UPDATE match_stats
            SET
                shot_quality = ?,
                conversion_rate = ?,
                shot_efficiency = ?,
                shot_volume_index = ?
            WHERE match_id = ? AND is_home = ?
        ''', updates)

        conn.commit()
        logger.info(f"Updated shot quality metrics for {len(updates)} match records")

        # Show sample results
        cursor.execute('''
            SELECT
                m.date,
                m.home_team_id,
                m.away_team_id,
                ms_h.shots,
                ms_h.shots_on_target,
                m.home_score,
                ms_h.shot_quality,
                ms_h.conversion_rate,
                ms_h.shot_efficiency
            FROM matches m
            JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
            WHERE m.league = 'EPL'
            ORDER BY m.date DESC
            LIMIT 5
        ''')

        logger.info("\n=== Sample Results (Recent EPL) ===")
        for row in cursor.fetchall():
            date, home, away, shots, sot, goals, sq, cr, se = row
            logger.info(f"{date} {home} vs {away}")
            logger.info(f"  Shots: {shots}, SoT: {sot}, Goals: {goals}")
            logger.info(f"  Quality: {sq:.3f}, Conversion: {cr:.3f}, Efficiency: {se:.3f}")

        return len(updates)

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def generate_quality_report(league='EPL', limit=10):
    """
    Generate a report of best/worst attacking performances by shot quality
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        logger.info(f"\n=== Top {limit} Shot Quality Performances ({league}) ===")

        cursor.execute(f'''
            SELECT
                m.date,
                CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
                ms.shots,
                ms.shots_on_target,
                CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END as goals,
                ms.shot_quality,
                ms.conversion_rate,
                ms.shot_efficiency
            FROM match_stats ms
            JOIN matches m ON ms.match_id = m.match_id
            WHERE m.league = '{league}'
            AND ms.shots >= 10
            ORDER BY ms.shot_quality DESC
            LIMIT {limit}
        ''')

        for i, row in enumerate(cursor.fetchall(), 1):
            date, team, shots, sot, goals, sq, cr, se = row
            logger.info(f"{i}. {team} ({date})")
            logger.info(f"   {shots} shots, {sot} SoT, {goals} goals")
            logger.info(f"   Quality: {sq:.1%}, Conv: {cr:.1%}, Eff: {se:.1%}")

        logger.info(f"\n=== Worst {limit} Shot Quality ({league}) ===")

        cursor.execute(f'''
            SELECT
                m.date,
                CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
                ms.shots,
                ms.shots_on_target,
                CASE WHEN ms.is_home = 1 THEN m.home_score ELSE m.away_score END as goals,
                ms.shot_quality,
                ms.conversion_rate,
                ms.shot_efficiency
            FROM match_stats ms
            JOIN matches m ON ms.match_id = m.match_id
            WHERE m.league = '{league}'
            AND ms.shots >= 10
            ORDER BY ms.shot_quality ASC
            LIMIT {limit}
        ''')

        for i, row in enumerate(cursor.fetchall(), 1):
            date, team, shots, sot, goals, sq, cr, se = row
            logger.info(f"{i}. {team} ({date})")
            logger.info(f"   {shots} shots, {sot} SoT, {goals} goals")
            logger.info(f"   Quality: {sq:.1%}, Conv: {cr:.1%}, Eff: {se:.1%}")

    finally:
        conn.close()


def main():
    """Main execution"""
    logger.info("=== Shot Quality Metrics Generator ===")

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return

    # Calculate metrics
    updated = calculate_shot_quality_metrics()
    logger.info(f"✅ Calculated metrics for {updated} match records")

    # Generate sample reports
    for league in ['EPL', 'LaLiga', 'Bundesliga']:
        generate_quality_report(league, limit=5)

    logger.info("\n=== Complete ===")
    logger.info("Shot quality metrics are now available as xG alternatives:")
    logger.info("  - shot_quality: Accuracy (SoT/Shots)")
    logger.info("  - conversion_rate: Finishing (Goals/SoT)")
    logger.info("  - shot_efficiency: Overall (Goals/Shots)")
    logger.info("  - shot_volume_index: Volume vs league average")


if __name__ == "__main__":
    main()
