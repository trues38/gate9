#!/usr/bin/env python3
"""
Understat xG Collector with Selenium

Crawls Understat for xG data using Selenium for JavaScript rendering.
Supports: EPL, LaLiga, Bundesliga, SerieA, Ligue1
"""

import sqlite3
import time
import json
import re
from pathlib import Path
from datetime import datetime
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# League mapping: Understat name -> Our DB name
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


def setup_driver():
    """Setup headless Chrome driver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("✅ Chrome driver initialized")
        return driver
    except Exception as e:
        logger.error(f"❌ Failed to initialize Chrome driver: {e}")
        logger.info("💡 Try installing ChromeDriver: brew install chromedriver")
        raise


def extract_json_from_script(driver, var_name):
    """
    Extract JSON data from JavaScript variable in page source

    Args:
        driver: Selenium WebDriver
        var_name: JavaScript variable name to extract

    Returns:
        dict: Parsed JSON data or empty dict
    """
    try:
        # Get page source after JavaScript execution
        page_source = driver.page_source

        # Look for JSON.parse() pattern
        pattern = rf"var\s+{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
        match = re.search(pattern, page_source)

        if not match:
            # Try alternative pattern without var
            pattern = rf"{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
            match = re.search(pattern, page_source)

        if not match:
            logger.warning(f"Could not find {var_name} in page source")
            return {}

        # Decode unicode escapes
        json_str = match.group(1)
        json_str = json_str.encode().decode('unicode_escape')

        # Parse JSON
        data = json.loads(json_str)
        logger.debug(f"Extracted {len(data)} items from {var_name}")
        return data

    except Exception as e:
        logger.error(f"Error extracting {var_name}: {e}")
        return {}


def fetch_league_xg(driver, league_understat, season='2024'):
    """
    Fetch xG data for a league from Understat

    Args:
        driver: Selenium WebDriver
        league_understat: League name in Understat (EPL, La_liga, etc.)
        season: Season year (2024 = 2024/25)

    Returns:
        dict: Match data with xG
    """
    url = f"https://understat.com/league/{league_understat}/{season}"
    logger.info(f"Fetching {league_understat} {season} from {url}")

    try:
        driver.get(url)

        # Wait for page to load
        time.sleep(3)

        # Try to find data in different variables
        for var_name in ['datesData', 'matchesData', 'JSON_data']:
            data = extract_json_from_script(driver, var_name)
            if data:
                logger.info(f"✅ Found {len(data)} matches in {var_name}")
                return data

        # If no data found in variables, try alternative method
        logger.warning(f"No data found in standard variables for {league_understat}")

        # Try to extract from window object using JavaScript
        try:
            script = "return window.datesData || window.matchesData || {};"
            data = driver.execute_script(script)
            if data:
                logger.info(f"✅ Found {len(data)} matches via JavaScript execution")
                return data
        except Exception as e:
            logger.debug(f"JavaScript execution failed: {e}")

        return {}

    except Exception as e:
        logger.error(f"Error fetching {league_understat}: {e}")
        return {}


def normalize_team_name(name):
    """Normalize team name to match SQLite team_id format"""
    name = name.lower()
    name = re.sub(r"['\\s\\-\\.]+", '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def update_match_xg(conn, match_data, league):
    """
    Update xG data in SQLite for a match

    Args:
        conn: SQLite connection
        match_data: Match data from Understat
        league: League name in our DB

    Returns:
        bool: True if updated successfully
    """
    try:
        # Extract data
        home_team = match_data['h']['title']
        away_team = match_data['a']['title']
        home_xg = float(match_data['xG']['h'])
        away_xg = float(match_data['xG']['a'])

        # Extract date and convert format
        # Understat: "2024-08-16 19:00:00" -> DB: "16/08/2024"
        date_str = match_data['datetime']
        date_parts = date_str[:10].split('-')  # ['2024', '08', '16']
        date_db_format = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"  # "16/08/2024"

        home_id = normalize_team_name(home_team)
        away_id = normalize_team_name(away_team)

        # Update home team xG
        cursor = conn.execute('''
            UPDATE match_stats
            SET xg = ?, xga = ?
            WHERE match_id IN (
                SELECT match_id FROM matches
                WHERE league = ?
                AND date = ?
                AND home_team_id LIKE ?
                AND away_team_id LIKE ?
            )
            AND is_home = 1
        ''', (home_xg, away_xg, league, date_db_format, f"%{home_id}%", f"%{away_id}%"))

        home_updated = cursor.rowcount

        # Update away team xG
        cursor = conn.execute('''
            UPDATE match_stats
            SET xg = ?, xga = ?
            WHERE match_id IN (
                SELECT match_id FROM matches
                WHERE league = ?
                AND date = ?
                AND home_team_id LIKE ?
                AND away_team_id LIKE ?
            )
            AND is_home = 0
        ''', (away_xg, home_xg, league, date_db_format, f"%{home_id}%", f"%{away_id}%"))

        away_updated = cursor.rowcount

        if home_updated > 0 or away_updated > 0:
            logger.debug(f"✅ {home_team} vs {away_team}: {home_xg:.2f} - {away_xg:.2f}")
            return True
        else:
            logger.debug(f"⚠️  Match not found in DB: {home_team} vs {away_team} ({date_db_format})")
            return False

    except Exception as e:
        logger.error(f"Error updating match: {e}")
        return False


def collect_league_xg(driver, league_understat, league_code, season='2024'):
    """
    Collect xG data for a league and update SQLite

    Args:
        driver: Selenium WebDriver
        league_understat: League name in Understat
        league_code: League code in our DB
        season: Season year

    Returns:
        int: Number of matches updated
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Collecting {league_code}")
    logger.info(f"{'='*60}")

    # Fetch data
    matches = fetch_league_xg(driver, league_understat, season)

    if not matches:
        logger.warning(f"❌ No data for {league_code}")
        return 0

    # Connect to DB
    conn = sqlite3.connect(str(DB_PATH))

    updated_count = 0

    try:
        # Handle both list and dict formats
        if isinstance(matches, list):
            # New format: list of match objects
            for match_data in matches:
                if update_match_xg(conn, match_data, league_code):
                    updated_count += 1
        elif isinstance(matches, dict):
            # Old format: dict of match objects
            for match_id, match_data in matches.items():
                if update_match_xg(conn, match_data, league_code):
                    updated_count += 1

        conn.commit()
        logger.info(f"✅ {league_code}: Updated {updated_count}/{len(matches)} matches")

    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

    return updated_count


def main():
    """Main collection routine"""
    logger.info("="*60)
    logger.info("Understat xG Collection (Selenium)")
    logger.info("="*60)

    if not DB_PATH.exists():
        logger.error(f"❌ Database not found: {DB_PATH}")
        return

    # Setup Selenium driver
    driver = None
    try:
        driver = setup_driver()

        total_updated = 0

        # Collect current season (2024/25)
        for understat_name, league_code in LEAGUES.items():
            try:
                count = collect_league_xg(driver, understat_name, league_code, '2024')
                total_updated += count

                # Rate limiting: 3-5 seconds between leagues
                if understat_name != list(LEAGUES.keys())[-1]:
                    delay = 4
                    logger.info(f"⏳ Waiting {delay}s before next league...")
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"❌ Error collecting {league_code}: {e}")
                continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Collection Complete")
        logger.info(f"{'='*60}")
        logger.info(f"Total matches updated: {total_updated}")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("🔒 Browser closed")


if __name__ == "__main__":
    main()
