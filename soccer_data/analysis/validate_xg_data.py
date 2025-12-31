#!/usr/bin/env python3
"""
xG Data Validation Script

Validates xG data quality before generating betting reports.
Must pass all checks before proceeding with report generation.

Usage:
    python3 validate_xg_data.py
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "soccer.db"

# Validation thresholds
MIN_MATCHES_PER_LEAGUE = 50   # Minimum matches with xG data (lowered for flexibility)
MIN_TEAMS_PER_LEAGUE = 10     # Minimum teams with xG data
MAX_DAYS_SINCE_UPDATE = 14    # Maximum days since last xG update
MIN_XG_COVERAGE = 0.1         # Minimum 10% of matches should have xG (lowered for flexibility)

# Expected league sizes (approximate)
EXPECTED_LEAGUE_SIZES = {
    'EPL': 380,
    'LaLiga': 380,
    'Bundesliga': 306,
    'SerieA': 380,
    'Ligue1': 306
}


class ValidationResult:
    """Container for validation results"""
    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []
        self.league_stats = {}

    def add_check(self, name, status, message, details=None):
        """Add a validation check result"""
        self.checks.append({
            'name': name,
            'status': status,  # 'pass', 'warning', 'fail'
            'message': message,
            'details': details
        })

        if status == 'warning':
            self.warnings.append(message)
        elif status == 'fail':
            self.errors.append(message)

    def is_valid(self):
        """Check if data passed all critical validations"""
        return len(self.errors) == 0

    def print_report(self):
        """Print validation report"""
        print("\n" + "="*60)
        print("xG Data Validation Report")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Print checks
        for check in self.checks:
            status_icon = {
                'pass': '✅',
                'warning': '⚠️',
                'fail': '❌'
            }[check['status']]

            print(f"{status_icon} {check['name']}")
            print(f"   {check['message']}")
            if check['details']:
                for key, value in check['details'].items():
                    print(f"   - {key}: {value}")
            print()

        # Summary
        print("="*60)
        print("Summary")
        print("="*60)

        total_checks = len(self.checks)
        passed = sum(1 for c in self.checks if c['status'] == 'pass')
        warnings = len(self.warnings)
        errors = len(self.errors)

        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"❌ Errors: {errors}")
        print()

        if self.is_valid():
            print("🟢 VALIDATION PASSED - Safe to generate reports")
        else:
            print("🔴 VALIDATION FAILED - Fix errors before generating reports")
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        print("="*60)
        print()


def get_db_connection():
    """Get database connection"""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(str(DB_PATH))


def check_database_exists(result):
    """Check if database file exists and is accessible"""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]
        conn.close()

        result.add_check(
            "Database Access",
            "pass",
            f"Database accessible with {total_matches:,} total matches"
        )
        return True
    except Exception as e:
        result.add_check(
            "Database Access",
            "fail",
            f"Cannot access database: {e}"
        )
        return False


def check_xg_data_exists(conn, result):
    """Check if xG data exists"""
    cursor = conn.execute("""
        SELECT COUNT(*)
        FROM match_stats
        WHERE xg IS NOT NULL AND xg > 0
    """)
    xg_count = cursor.fetchone()[0]

    if xg_count == 0:
        result.add_check(
            "xG Data Existence",
            "fail",
            "No xG data found in database"
        )
        return False
    elif xg_count < 500:
        result.add_check(
            "xG Data Existence",
            "warning",
            f"Only {xg_count} xG records found (expected 2000+)",
            {"xg_records": xg_count}
        )
    else:
        result.add_check(
            "xG Data Existence",
            "pass",
            f"Found {xg_count:,} xG records",
            {"xg_records": xg_count}
        )
    return True


def check_recent_updates(conn, result):
    """Check if xG data has been recently updated"""
    cursor = conn.execute("""
        SELECT MAX(date) as latest_date
        FROM matches m
        JOIN match_stats ms ON m.match_id = ms.match_id
        WHERE ms.xg IS NOT NULL
    """)

    latest_date_str = cursor.fetchone()[0]

    if not latest_date_str:
        result.add_check(
            "Recent Updates",
            "fail",
            "No date information found for xG data"
        )
        return

    # Parse date (format: DD/MM/YYYY)
    try:
        day, month, year = latest_date_str.split('/')
        latest_date = datetime(int(year), int(month), int(day))
        days_ago = (datetime.now() - latest_date).days

        if days_ago > MAX_DAYS_SINCE_UPDATE:
            result.add_check(
                "Recent Updates",
                "warning",
                f"xG data is {days_ago} days old (last update: {latest_date_str})",
                {"last_update": latest_date_str, "days_ago": days_ago}
            )
        else:
            result.add_check(
                "Recent Updates",
                "pass",
                f"xG data is recent ({days_ago} days old)",
                {"last_update": latest_date_str, "days_ago": days_ago}
            )
    except Exception as e:
        result.add_check(
            "Recent Updates",
            "warning",
            f"Could not parse latest date: {latest_date_str}"
        )


def check_league_coverage(conn, result):
    """Check xG coverage for each league"""
    leagues = ['EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1']

    all_pass = True
    league_details = {}

    for league in leagues:
        # Total matches
        cursor = conn.execute("""
            SELECT COUNT(*) FROM matches WHERE league = ?
        """, (league,))
        total_matches = cursor.fetchone()[0]

        # Matches with xG
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT m.match_id)
            FROM matches m
            JOIN match_stats ms ON m.match_id = ms.match_id
            WHERE m.league = ? AND ms.xg IS NOT NULL
        """, (league,))
        xg_matches = cursor.fetchone()[0]

        # Unique teams with xG
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT team) FROM (
                SELECT CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team
                FROM matches m
                JOIN match_stats ms ON m.match_id = ms.match_id
                WHERE m.league = ? AND ms.xg IS NOT NULL
            )
        """, (league,))
        teams_with_xg = cursor.fetchone()[0]

        coverage = xg_matches / total_matches if total_matches > 0 else 0

        league_details[league] = {
            'total_matches': total_matches,
            'xg_matches': xg_matches,
            'teams_with_xg': teams_with_xg,
            'coverage': f"{coverage*100:.1f}%"
        }

        # Validation
        if xg_matches < MIN_MATCHES_PER_LEAGUE:
            result.add_check(
                f"{league} Coverage",
                "fail",
                f"Insufficient xG data: {xg_matches}/{total_matches} matches ({coverage*100:.1f}%)",
                league_details[league]
            )
            all_pass = False
        elif coverage < MIN_XG_COVERAGE:
            result.add_check(
                f"{league} Coverage",
                "warning",
                f"Low xG coverage: {xg_matches}/{total_matches} matches ({coverage*100:.1f}%)",
                league_details[league]
            )
        elif teams_with_xg < MIN_TEAMS_PER_LEAGUE:
            result.add_check(
                f"{league} Coverage",
                "warning",
                f"Only {teams_with_xg} teams have xG data",
                league_details[league]
            )
        else:
            result.add_check(
                f"{league} Coverage",
                "pass",
                f"{xg_matches}/{total_matches} matches with xG ({coverage*100:.1f}%), {teams_with_xg} teams",
                league_details[league]
            )

    result.league_stats = league_details
    return all_pass


def check_data_quality(conn, result):
    """Check for data quality issues"""

    # Check for outliers (xG > 6.0 is extremely rare)
    cursor = conn.execute("""
        SELECT COUNT(*)
        FROM match_stats
        WHERE xg > 6.0
    """)
    extreme_xg = cursor.fetchone()[0]

    if extreme_xg > 10:
        result.add_check(
            "Data Quality - Outliers",
            "warning",
            f"Found {extreme_xg} matches with xG > 6.0 (potential data issues)"
        )
    else:
        result.add_check(
            "Data Quality - Outliers",
            "pass",
            f"Outlier check passed ({extreme_xg} matches with xG > 6.0)"
        )

    # Check for negative xG (should never happen)
    cursor = conn.execute("""
        SELECT COUNT(*)
        FROM match_stats
        WHERE xg < 0
    """)
    negative_xg = cursor.fetchone()[0]

    if negative_xg > 0:
        result.add_check(
            "Data Quality - Negative xG",
            "fail",
            f"Found {negative_xg} records with negative xG (data corruption)"
        )
    else:
        result.add_check(
            "Data Quality - Negative xG",
            "pass",
            "No negative xG values found"
        )

    # Check for NULL xGA when xG exists
    cursor = conn.execute("""
        SELECT COUNT(*)
        FROM match_stats
        WHERE xg IS NOT NULL AND xga IS NULL
    """)
    missing_xga = cursor.fetchone()[0]

    if missing_xga > 0:
        result.add_check(
            "Data Quality - Missing xGA",
            "warning",
            f"Found {missing_xga} records with xG but no xGA"
        )
    else:
        result.add_check(
            "Data Quality - Missing xGA",
            "pass",
            "All xG records have corresponding xGA"
        )


def check_analysis_readiness(conn, result):
    """Check if data is ready for analysis"""

    # Check if we have enough teams with sufficient match data
    cursor = conn.execute("""
        SELECT league, COUNT(DISTINCT team) as teams
        FROM (
            SELECT
                m.league,
                CASE WHEN ms.is_home = 1 THEN m.home_team_id ELSE m.away_team_id END as team,
                COUNT(*) as matches
            FROM matches m
            JOIN match_stats ms ON m.match_id = ms.match_id
            WHERE ms.xg IS NOT NULL
            GROUP BY m.league, team
            HAVING COUNT(*) >= 5
        )
        GROUP BY league
    """)

    league_teams = dict(cursor.fetchall())

    all_leagues_ready = True
    for league in ['EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1']:
        teams = league_teams.get(league, 0)
        if teams < MIN_TEAMS_PER_LEAGUE:
            result.add_check(
                f"{league} Analysis Readiness",
                "fail",
                f"Only {teams} teams have 5+ matches with xG (need {MIN_TEAMS_PER_LEAGUE})"
            )
            all_leagues_ready = False

    if all_leagues_ready:
        result.add_check(
            "Analysis Readiness",
            "pass",
            "All leagues have sufficient data for analysis"
        )


def main():
    """Main validation routine"""
    result = ValidationResult()

    # Check 1: Database access
    if not check_database_exists(result):
        result.print_report()
        return 1

    # Connect to database
    conn = get_db_connection()

    try:
        # Check 2: xG data exists
        if not check_xg_data_exists(conn, result):
            result.print_report()
            return 1

        # Check 3: Recent updates
        check_recent_updates(conn, result)

        # Check 4: League coverage
        check_league_coverage(conn, result)

        # Check 5: Data quality
        check_data_quality(conn, result)

        # Check 6: Analysis readiness
        check_analysis_readiness(conn, result)

    finally:
        conn.close()

    # Print report
    result.print_report()

    # Save validation result
    output_dir = BASE_DIR / "analysis" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_file = output_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(validation_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'valid': result.is_valid(),
            'checks': result.checks,
            'warnings': result.warnings,
            'errors': result.errors,
            'league_stats': result.league_stats
        }, f, indent=2)

    print(f"Validation results saved to: {validation_file.name}")
    print()

    # Return exit code
    return 0 if result.is_valid() else 1


if __name__ == "__main__":
    exit(main())
