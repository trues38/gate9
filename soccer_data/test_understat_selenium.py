#!/usr/bin/env python3
"""
Test Understat Selenium collector with EPL only
"""

import sys
from pathlib import Path

# Add collectors to path
sys.path.insert(0, str(Path(__file__).parent / 'collectors'))

from understat_selenium_collector import (
    setup_driver,
    fetch_league_xg,
    collect_league_xg
)

import logging
logging.basicConfig(level=logging.INFO)

def test_epl():
    """Test EPL collection only"""
    print("=== Testing Understat Selenium Collector ===\n")

    # Setup driver
    driver = setup_driver()

    try:
        # Test EPL only
        print("\n1. Testing EPL fetch...")
        matches = fetch_league_xg(driver, 'EPL', '2024')

        if matches:
            print(f"✅ Found {len(matches)} EPL matches")

            # Show first 3 matches
            print("\nSample matches:")
            for i, match_data in enumerate(matches[:3]):
                home = match_data['h']['title']
                away = match_data['a']['title']
                home_xg = match_data['xG']['h']
                away_xg = match_data['xG']['a']
                date = match_data['datetime'][:10]

                print(f"  {date}: {home} {home_xg} - {away_xg} {away}")

            # Test DB update
            print("\n2. Testing database update...")
            updated = collect_league_xg(driver, 'EPL', 'EPL', '2024')
            print(f"✅ Updated {updated} matches in database")

        else:
            print("❌ No matches found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n✅ Test complete")

if __name__ == "__main__":
    test_epl()
