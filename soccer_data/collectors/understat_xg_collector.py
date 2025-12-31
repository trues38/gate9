#!/usr/bin/env python3
"""
Understat xG Collector

Crawls Understat for xG data and updates SQLite database.
Supports: EPL, LaLiga, Bundesliga, SerieA, Ligue1
"""

import requests
import json
import re
import sqlite3
import time
import random
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# League mapping
LEAGUES = {
    'EPL': 'EPL',
    'La_liga': 'LaLiga',
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'SerieA',
    'Ligue_1': 'Ligue1'
}

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"

# Headers to avoid bot detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://www.google.com/'
}


def normalize_team_name(name: str) -> str:
    """Normalize team name to match SQLite team_id format"""
    name = name.lower()
    name = re.sub(r"['\s\-\.]+", '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def extract_json_var(html: str, var_name: str) -> dict:
    """Extract JSON from JavaScript variable in HTML"""
    pattern = rf'{var_name}\s*=\s*JSON\.parse\(\'(.+?)\'\)'
    matches = re.findall(pattern, html)

    if not matches:
        logger.warning(f"Could not find {var_name} in HTML")
        return {}

    try:
        # Decode unicode escapes
        json_str = matches[0].encode().decode('unicode_escape')
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error parsing JSON from {var_name}: {e}")
        return {}


def fetch_league_data(league: str, season: str = '2024') -> dict:
    """
    Fetch xG data for a league from Understat

    Args:
        league: League name (EPL, La_liga, etc.)
        season: Season year (2024 = 2024/25 season)

    Returns:
        Dictionary with match data
    """
    url = f"https://understat.com/league/{league}/{season}"
    logger.info(f"Fetching {league} {season} from {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # Extract match data from datesData variable
        matches_data = extract_json_var(response.text, 'datesData')

        if not matches_data:
            logger.warning(f"No match data found for {league} {season}")
            return {}

        logger.info(f"Found {len(matches_data)} matches for {league}")
        return matches_data

    except requests.RequestException as e:
        logger.error(f"Error fetching {league}: {e}")
        return {}


def update_match_xg(conn: sqlite3.Connection, match_data: dict, league: str):
    """
    Update xG data in SQLite for a match

    Args:
        conn: SQLite connection
        match_data: Match data from Understat
        league: League name
    """
    try:
        # Extract data
        home_team = match_data['h']['title']
        away_team = match_data['a']['title']
        home_xg = float(match_data['xG']['h'])
        away_xg = float(match_data['xG']['a'])
        date = match_data['datetime'][:10]  # YYYY-MM-DD

        home_id = normalize_team_name(home_team)
        away_id = normalize_team_name(away_team)

        # Update home team xG
        cursor = conn.execute('''
            UPDATE match_stats
            SET xg = ?, xga = ?
            WHERE match_id IN (
                SELECT match_id FROM matches
                WHERE league = ?
                AND date LIKE ?
                AND home_team_id LIKE ?
                AND away_team_id LIKE ?
            )
            AND is_home = 1
        ''', (home_xg, away_xg, league, f"{date}%", f"%{home_id}%", f"%{away_id}%"))

        home_updated = cursor.rowcount

        # Update away team xG
        cursor = conn.execute('''
            UPDATE match_stats
            SET xg = ?, xga = ?
            WHERE match_id IN (
                SELECT match_id FROM matches
                WHERE league = ?
                AND date LIKE ?
                AND home_team_id LIKE ?
                AND away_team_id LIKE ?
            )
            AND is_home = 0
        ''', (away_xg, home_xg, league, f"{date}%", f"%{home_id}%", f"%{away_id}%"))

        away_updated = cursor.rowcount

        if home_updated > 0 or away_updated > 0:
            logger.debug(f"Updated xG for {home_team} vs {away_team}: {home_xg:.2f} - {away_xg:.2f}")
            return True
        else:
            # Match not found in SQLite, might be too new
            logger.debug(f"Match not found in DB: {home_team} vs {away_team} ({date})")
            return False

    except Exception as e:
        logger.error(f"Error updating match: {e}")
        return False


def collect_league_xg(league_understat: str, league_code: str, season: str = '2024'):
    """
    Collect xG data for a league and update SQLite

    Args:
        league_understat: League name in Understat (e.g., 'EPL', 'La_liga')
        league_code: League code in our DB (e.g., 'EPL', 'LaLiga')
        season: Season year
    """
    logger.info(f"\n=== Collecting {league_code} ===")

    # Fetch data
    matches = fetch_league_data(league_understat, season)

    if not matches:
        logger.warning(f"No data for {league_code}")
        return 0

    # Connect to DB
    conn = sqlite3.connect(str(DB_PATH))

    updated_count = 0

    try:
        # Process each match
        for match_id, match_data in matches.items():
            if update_match_xg(conn, match_data, league_code):
                updated_count += 1

        conn.commit()
        logger.info(f"{league_code}: Updated {updated_count}/{len(matches)} matches")

    finally:
        conn.close()

    return updated_count


def main():
    """Main collection routine"""
    logger.info("=== Understat xG Collection Started ===")
    start_time = time.time()

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return

    total_updated = 0

    # Collect current season (2024/25)
    for understat_name, league_code in LEAGUES.items():
        try:
            count = collect_league_xg(understat_name, league_code, '2024')
            total_updated += count

            # Rate limiting: 3-5 seconds between leagues
            if understat_name != list(LEAGUES.keys())[-1]:  # Not last league
                delay = random.uniform(3, 5)
                logger.info(f"Waiting {delay:.1f}s before next league...")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Error collecting {league_code}: {e}")
            continue

    elapsed = time.time() - start_time
    logger.info(f"\n=== Collection Complete ===")
    logger.info(f"Total matches updated: {total_updated}")
    logger.info(f"Time elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
