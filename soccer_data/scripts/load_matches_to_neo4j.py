#!/usr/bin/env python3
"""
Load Match nodes from SQLite to Neo4j

Enables Graph RAG queries:
- Recent form analysis (last 5 games)
- Head-to-head history
- xG trend analysis (IMPROVING/DECLINING)
- Referee-team relationship analysis
"""

import sqlite3
from pathlib import Path
from neo4j import GraphDatabase
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / "data" / "soccer.db"

# Neo4j connection (VPS - corrected)
NEO4J_URI = 'bolt://localhost:7689'  # Soccer DB port
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'soccer_g9_2025'  # Correct password


class MatchLoader:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
        self.sqlite_conn.row_factory = sqlite3.Row

    def close(self):
        self.neo4j_driver.close()
        self.sqlite_conn.close()

    def load_matches(self):
        """Load all matches from SQLite to Neo4j"""
        cursor = self.sqlite_conn.cursor()

        # Get matches with xG data and stats
        # match_stats has 2 rows per match (home + away)
        cursor.execute("""
            SELECT
                m.match_id,
                m.date,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.league,
                m.season,
                m.referee_id,
                home_stats.xg as home_xG,
                away_stats.xg as away_xG,
                home_stats.shots as home_shots,
                away_stats.shots as away_shots,
                home_stats.shots_on_target as home_shots_on_target,
                away_stats.shots_on_target as away_shots_on_target,
                home_stats.possession as home_possession,
                away_stats.possession as away_possession
            FROM matches m
            LEFT JOIN match_stats home_stats
                ON m.match_id = home_stats.match_id AND home_stats.is_home = 1
            LEFT JOIN match_stats away_stats
                ON m.match_id = away_stats.match_id AND away_stats.is_home = 0
            WHERE m.date IS NOT NULL
            ORDER BY m.date ASC
        """)

        matches = cursor.fetchall()
        logger.info(f"Found {len(matches)} matches in SQLite")

        count = 0
        with self.neo4j_driver.session() as session:
            for match in matches:
                # Determine result
                if match['home_score'] is not None and match['away_score'] is not None:
                    if match['home_score'] > match['away_score']:
                        result = 'HOME_WIN'
                    elif match['away_score'] > match['home_score']:
                        result = 'AWAY_WIN'
                    else:
                        result = 'DRAW'
                else:
                    result = None

                # Parse date to ISO format (DD/MM/YYYY -> YYYY-MM-DD)
                date_str = match['date']
                if '/' in date_str:
                    day, month, year = date_str.split('/')
                    iso_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    iso_date = date_str

                # Create Match node
                session.run('''
                    MERGE (m:Match {match_id: $match_id})
                    SET m.date = date($date),
                        m.league = $league,
                        m.season = $season,
                        m.home_score = $home_score,
                        m.away_score = $away_score,
                        m.result = $result,
                        m.home_xG = $home_xG,
                        m.away_xG = $away_xG,
                        m.home_shots = $home_shots,
                        m.away_shots = $away_shots,
                        m.home_possession = $home_possession,
                        m.away_possession = $away_possession
                ''',
                    match_id=match['match_id'],
                    date=iso_date,
                    league=match['league'],
                    season=match['season'],
                    home_score=match['home_score'],
                    away_score=match['away_score'],
                    result=result,
                    home_xG=match['home_xG'],
                    away_xG=match['away_xG'],
                    home_shots=match['home_shots'],
                    away_shots=match['away_shots'],
                    home_possession=match['home_possession'],
                    away_possession=match['away_possession']
                )

                # Link Match -> Home Team
                if match['home_team_id']:
                    session.run('''
                        MATCH (m:Match {match_id: $match_id})
                        MATCH (t:Team {team_id: $team_id})
                        MERGE (t)-[:PLAYED_HOME]->(m)
                    ''', match_id=match['match_id'], team_id=match['home_team_id'])

                # Link Match -> Away Team
                if match['away_team_id']:
                    session.run('''
                        MATCH (m:Match {match_id: $match_id})
                        MATCH (t:Team {team_id: $team_id})
                        MERGE (t)-[:PLAYED_AWAY]->(m)
                    ''', match_id=match['match_id'], team_id=match['away_team_id'])

                # Link Match -> Referee
                if match['referee_id']:
                    session.run('''
                        MATCH (m:Match {match_id: $match_id})
                        MERGE (r:Referee {referee_id: $referee_id})
                        MERGE (r)-[:OFFICIATED]->(m)
                    ''', match_id=match['match_id'], referee_id=match['referee_id'])

                count += 1
                if count % 500 == 0:
                    logger.info(f"Loaded {count} matches...")

        logger.info(f"✅ Loaded {count} matches to Neo4j")
        return count

    def create_form_sequences(self):
        """Create NEXT_MATCH relationships for form analysis"""
        logger.info("Creating form sequences...")

        with self.neo4j_driver.session() as session:
            # For each team, link matches in chronological order
            result = session.run('''
                MATCH (t:Team)
                RETURN t.team_id as team_id
            ''')

            teams = [r['team_id'] for r in result]

            for team_id in teams:
                # Get all matches for this team (home or away)
                session.run('''
                    MATCH (t:Team {team_id: $team_id})
                    MATCH (t)-[:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
                    WITH m ORDER BY m.date ASC
                    WITH collect(m) as matches
                    UNWIND range(0, size(matches)-2) as i
                    WITH matches[i] as m1, matches[i+1] as m2
                    MERGE (m1)-[:NEXT_MATCH {team_id: $team_id}]->(m2)
                ''', team_id=team_id)

        logger.info("✅ Form sequences created")

    def get_stats(self):
        """Get loading statistics"""
        with self.neo4j_driver.session() as session:
            result = session.run('''
                MATCH (m:Match)
                WITH count(m) as total,
                     sum(CASE WHEN m.home_xG IS NOT NULL THEN 1 ELSE 0 END) as with_xG
                RETURN total, with_xG,
                       round(100.0 * with_xG / total, 1) as xG_coverage
            ''')
            stats = result.single()

            # Get date range
            result = session.run('''
                MATCH (m:Match)
                RETURN min(m.date) as earliest, max(m.date) as latest
            ''')
            dates = result.single()

            return {
                'total_matches': stats['total'],
                'with_xG': stats['with_xG'],
                'xG_coverage': stats['xG_coverage'],
                'earliest_date': dates['earliest'],
                'latest_date': dates['latest']
            }


def main():
    loader = MatchLoader()

    try:
        # Load matches
        logger.info("=== Loading Matches to Neo4j ===")
        count = loader.load_matches()

        # Create form sequences
        logger.info("\n=== Creating Form Sequences ===")
        loader.create_form_sequences()

        # Get stats
        logger.info("\n=== Match Loading Statistics ===")
        stats = loader.get_stats()
        logger.info(f"Total matches: {stats['total_matches']}")
        logger.info(f"With xG data: {stats['with_xG']} ({stats['xG_coverage']}%)")
        logger.info(f"Date range: {stats['earliest_date']} to {stats['latest_date']}")

    finally:
        loader.close()


if __name__ == "__main__":
    main()
