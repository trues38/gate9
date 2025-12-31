#!/usr/bin/env python3
"""
Inspect Understat data structure
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'collectors'))

from understat_selenium_collector import setup_driver, fetch_league_xg
import json

driver = setup_driver()

try:
    matches = fetch_league_xg(driver, 'EPL', '2024')

    print(f"Data type: {type(matches)}")
    print(f"Length: {len(matches)}")

    if isinstance(matches, list):
        print("\n=== First match (list format) ===")
        first = matches[0]
        print(json.dumps(first, indent=2))
    elif isinstance(matches, dict):
        print("\n=== First match (dict format) ===")
        first_key = list(matches.keys())[0]
        print(f"Key: {first_key}")
        print(json.dumps(matches[first_key], indent=2))

finally:
    driver.quit()
