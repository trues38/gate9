#!/usr/bin/env python3
"""
Soccer Data Ingestion Script v1.0

Loads existing data into SQLite following the v1.0 architecture:
- Historical odds (football-data.co.uk format)
- Understat xG data
- Manager database
- Player form
- Injury data

Common IDs are generated for Neo4j linkage.
"""

import sqlite3
import json
import csv
import os
from pathlib import Path
from datetime import datetime
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"
SCHEMA_PATH = BASE_DIR / "schema" / "soccer_sqlite_schema.sql"
RAW_DATA = BASE_DIR / "raw_data"
PROCESSED_DATA = BASE_DIR / "processed"

# League mappings
LEAGUE_MAP = {
    'E0': 'EPL',
    'SP1': 'LaLiga',
    'D1': 'Bundesliga',
    'I1': 'SerieA',
    'F1': 'Ligue1',
    'EPL': 'EPL',
    'LaLiga': 'LaLiga',
    'Bundesliga': 'Bundesliga',
    'SerieA': 'SerieA',
    'Ligue1': 'Ligue1'
}

# Team ID normalization
def normalize_team_id(team_name: str) -> str:
    """Generate consistent team_id from team name"""
    # Remove common prefixes/suffixes
    name = team_name.lower()
    name = re.sub(r"['\s\-\.]+", '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name

def normalize_manager_id(manager_name: str) -> str:
    """Generate consistent manager_id"""
    name = manager_name.lower()
    name = re.sub(r"['\s\-\.]+", '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def normalize_referee_id(referee_name: str) -> str:
    """Generate consistent referee_id"""
    name = referee_name.lower()
    name = re.sub(r"['\s\-\.]+", '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def generate_match_id(league: str, date: str, home: str, away: str) -> str:
    """Generate consistent match_id for Common ID system"""
    # Format: LEAGUE_SEASON_home_away_YYYYMMDD
    date_clean = date.replace('-', '').replace('/', '')
    if len(date_clean) == 8 and date_clean[:2] in ['19', '20']:
        # YYYYMMDD format
        pass
    elif len(date_clean) == 8:
        # DDMMYYYY format -> YYYYMMDD
        date_clean = date_clean[4:8] + date_clean[2:4] + date_clean[0:2]

    home_id = normalize_team_id(home)
    away_id = normalize_team_id(away)
    return f"{league}_{home_id}_{away_id}_{date_clean}"


class SoccerDataIngester:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()

    def init_schema(self):
        """Initialize database schema from SQL file"""
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()

        self.conn.executescript(schema_sql)
        self.conn.commit()
        logger.info("Schema initialized")

    def ingest_historical_odds(self):
        """Ingest historical odds from football-data.co.uk CSV files"""
        odds_dir = RAW_DATA / "historical_odds"
        if not odds_dir.exists():
            logger.warning(f"Odds directory not found: {odds_dir}")
            return 0

        total_matches = 0

        for csv_file in odds_dir.glob("*.csv"):
            # Extract league and season from filename (e.g., EPL_2425.csv)
            filename = csv_file.stem
            parts = filename.split('_')
            league = LEAGUE_MAP.get(parts[0], parts[0])
            season = f"20{parts[1][:2]}-{parts[1][2:]}" if len(parts) > 1 else "2024-25"

            logger.info(f"Processing {csv_file.name} ({league} {season})")

            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if not row.get('HomeTeam') or not row.get('AwayTeam'):
                        continue

                    # Generate IDs
                    home_team_id = normalize_team_id(row['HomeTeam'])
                    away_team_id = normalize_team_id(row['AwayTeam'])
                    referee_id = normalize_referee_id(row.get('Referee', '')) if row.get('Referee') else None

                    # Parse date
                    date_str = row.get('Date', '')

                    match_id = generate_match_id(league, date_str, row['HomeTeam'], row['AwayTeam'])

                    # Ensure teams exist
                    self._ensure_team(home_team_id, row['HomeTeam'], league)
                    self._ensure_team(away_team_id, row['AwayTeam'], league)

                    # Ensure referee exists
                    if referee_id:
                        self._ensure_referee(referee_id, row.get('Referee', ''))

                    # Insert match
                    try:
                        self.conn.execute('''
                            INSERT OR REPLACE INTO matches
                            (match_id, date, league, season, home_team_id, away_team_id,
                             home_score, away_score, referee_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            match_id, date_str, league, season,
                            home_team_id, away_team_id,
                            self._safe_int(row.get('FTHG')),
                            self._safe_int(row.get('FTAG')),
                            referee_id
                        ))
                    except sqlite3.Error as e:
                        logger.error(f"Error inserting match: {e}")
                        continue

                    # Insert match stats
                    for is_home, team_id, prefix in [(1, home_team_id, 'H'), (0, away_team_id, 'A')]:
                        try:
                            self.conn.execute('''
                                INSERT OR REPLACE INTO match_stats
                                (match_id, team_id, is_home, shots, shots_on_target,
                                 corners, fouls, yellow_cards, red_cards)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                match_id, team_id, is_home,
                                self._safe_int(row.get(f'{prefix}S')),
                                self._safe_int(row.get(f'{prefix}ST')),
                                self._safe_int(row.get(f'{prefix}C')),
                                self._safe_int(row.get(f'{prefix}F')),
                                self._safe_int(row.get(f'{prefix}Y')),
                                self._safe_int(row.get(f'{prefix}R'))
                            ))
                        except sqlite3.Error:
                            pass

                    # Insert closing odds
                    try:
                        self.conn.execute('''
                            INSERT OR REPLACE INTO odds_closing
                            (match_id, bookmaker, home_win, draw, away_win,
                             ah_line, ah_home, ah_away, ou_line, over, under)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            match_id, 'pinnacle',
                            self._safe_float(row.get('PSH')),
                            self._safe_float(row.get('PSD')),
                            self._safe_float(row.get('PSA')),
                            self._safe_float(row.get('AHh')),
                            self._safe_float(row.get('PAHH')),
                            self._safe_float(row.get('PAHA')),
                            2.5,  # Default O/U line
                            self._safe_float(row.get('P>2.5')),
                            self._safe_float(row.get('P<2.5'))
                        ))
                    except sqlite3.Error:
                        pass

                    total_matches += 1

            self.conn.commit()

        logger.info(f"Ingested {total_matches} matches from historical odds")
        return total_matches

    def ingest_understat_data(self):
        """Ingest Understat xG data"""
        understat_dir = RAW_DATA / "understat"
        if not understat_dir.exists():
            logger.warning(f"Understat directory not found: {understat_dir}")
            return 0

        total_updated = 0

        for league_dir in understat_dir.iterdir():
            if not league_dir.is_dir():
                continue

            league = LEAGUE_MAP.get(league_dir.name, league_dir.name)

            for year_dir in league_dir.iterdir():
                if not year_dir.is_dir():
                    continue

                results_file = year_dir / "results.json"
                if results_file.exists():
                    with open(results_file, 'r') as f:
                        results = json.load(f)

                    for match in results:
                        if not match.get('isResult'):
                            continue

                        # Try to match with existing match
                        home_id = normalize_team_id(match['h']['title'])
                        away_id = normalize_team_id(match['a']['title'])

                        # Update xG in match_stats
                        home_xg = self._safe_float(match.get('xG', {}).get('h'))
                        away_xg = self._safe_float(match.get('xG', {}).get('a'))

                        # Update by team
                        cursor = self.conn.execute('''
                            UPDATE match_stats SET xg = ?
                            WHERE team_id = ? AND is_home = 1
                            AND match_id IN (SELECT match_id FROM matches WHERE league = ?)
                        ''', (home_xg, home_id, league))

                        cursor = self.conn.execute('''
                            UPDATE match_stats SET xg = ?, xga = ?
                            WHERE team_id = ? AND is_home = 0
                            AND match_id IN (SELECT match_id FROM matches WHERE league = ?)
                        ''', (away_xg, home_xg, away_id, league))

                        total_updated += 1

        self.conn.commit()
        logger.info(f"Updated xG for {total_updated} matches")
        return total_updated

    def ingest_manager_database(self):
        """Ingest manager tactical profiles"""
        manager_file = PROCESSED_DATA / "manager_database.json"
        if not manager_file.exists():
            logger.warning(f"Manager database not found: {manager_file}")
            return 0

        with open(manager_file, 'r') as f:
            managers = json.load(f)

        count = 0
        for team_name, manager_data in managers.items():
            manager_id = normalize_manager_id(manager_data['name'])
            team_id = normalize_team_id(team_name)

            # Insert/update manager
            self.conn.execute('''
                INSERT OR REPLACE INTO managers (manager_id, name, nationality)
                VALUES (?, ?, ?)
            ''', (
                manager_id,
                manager_data['name'],
                manager_data.get('nationality', '')
            ))

            # Update team's manager if team exists
            # (Manager-Team relationship will be in Neo4j)
            count += 1

        self.conn.commit()
        logger.info(f"Ingested {count} managers")
        return count

    def ingest_injury_data(self):
        """Ingest injury data"""
        injury_file = PROCESSED_DATA / "injury_data.json"
        if not injury_file.exists():
            logger.warning(f"Injury data not found: {injury_file}")
            return 0

        with open(injury_file, 'r') as f:
            injuries = json.load(f)

        count = 0
        # Handle both list format and dict format
        injury_list = injuries if isinstance(injuries, list) else []

        for injury in injury_list:
            player_name = injury.get('player', '')
            if not player_name:
                continue

            # Use team from data or infer from league
            team_name = injury.get('team', 'unknown')
            league = injury.get('league', 'EPL')
            if team_name == 'Unknown':
                # Skip injuries with unknown team - can't link properly
                continue

            team_id = normalize_team_id(team_name)
            player_id = f"{normalize_team_id(player_name)}_{team_id}"

            # Ensure team exists first
            self._ensure_team(team_id, team_name, league)

            # Ensure player exists (without FK reference to allow flexibility)
            try:
                self.conn.execute('''
                    INSERT OR IGNORE INTO players (player_id, name, team_id)
                    VALUES (?, ?, ?)
                ''', (player_id, player_name, team_id))
            except sqlite3.IntegrityError:
                pass

            # Insert injury (without FK constraint)
            try:
                self.conn.execute('''
                    INSERT INTO injuries
                    (player_id, team_id, injury_type, status, expected_return, reported_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    player_id, team_id,
                    injury.get('injury_type', ''),
                    injury.get('status', 'out').lower(),
                    injury.get('expected_return', ''),
                    injury.get('date', datetime.now().isoformat())
                ))
                count += 1
            except sqlite3.IntegrityError:
                pass

        self.conn.commit()
        logger.info(f"Ingested {count} injuries")
        return count

    def _ensure_team(self, team_id: str, name: str, league: str):
        """Ensure team exists in database"""
        self.conn.execute('''
            INSERT OR IGNORE INTO teams (team_id, name, league)
            VALUES (?, ?, ?)
        ''', (team_id, name, league))

    def _ensure_referee(self, referee_id: str, name: str):
        """Ensure referee exists in database"""
        self.conn.execute('''
            INSERT OR IGNORE INTO referees (referee_id, name)
            VALUES (?, ?)
        ''', (referee_id, name))

    def _safe_int(self, val):
        """Safe integer conversion"""
        if val is None or val == '':
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _safe_float(self, val):
        """Safe float conversion"""
        if val is None or val == '':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def get_stats(self) -> dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        stats = {}
        tables = ['teams', 'managers', 'referees', 'players', 'matches',
                  'match_stats', 'odds_closing', 'injuries']

        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[table] = cursor.fetchone()[0]
            except sqlite3.Error:
                stats[table] = 0

        return stats


def main():
    ingester = SoccerDataIngester()

    try:
        ingester.connect()

        # Initialize schema
        logger.info("Initializing schema...")
        ingester.init_schema()

        # Ingest all data sources
        logger.info("\n=== Ingesting Historical Odds ===")
        ingester.ingest_historical_odds()

        logger.info("\n=== Ingesting Understat xG Data ===")
        ingester.ingest_understat_data()

        logger.info("\n=== Ingesting Manager Database ===")
        ingester.ingest_manager_database()

        logger.info("\n=== Ingesting Injury Data ===")
        ingester.ingest_injury_data()

        # Print stats
        stats = ingester.get_stats()
        logger.info("\n=== Database Statistics ===")
        for table, count in stats.items():
            if count > 0:
                logger.info(f"  {table}: {count:,}")

        db_size = ingester.db_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Database size: {db_size:.2f} MB")

    finally:
        ingester.close()


if __name__ == "__main__":
    main()
