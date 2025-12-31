#!/usr/bin/env python3
"""
Test xG data sources recommended by user
"""

import requests
from bs4 import BeautifulSoup
import json

print("=== Testing xG Data Sources ===\n")

# Test 1: FBref (StatsBomb data)
print("1. Testing FBref.com (EPL)")
try:
    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Look for xG in table headers
        tables = soup.find_all('table')
        xg_found = False
        for table in tables:
            if 'xG' in str(table):
                xg_found = True
                break
        print(f"✅ FBref accessible (status {response.status_code})")
        print(f"   xG data found: {xg_found}")
        print(f"   Tables found: {len(tables)}")
    else:
        print(f"⚠️  FBref returned status {response.status_code}")
except Exception as e:
    print(f"❌ FBref failed: {e}")

print()

# Test 2: Understat (re-test with proper method)
print("2. Testing Understat.com (EPL)")
try:
    url = "https://understat.com/league/EPL/2024"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        # Check if datesData exists
        has_dates_data = 'datesData' in response.text
        has_teams_data = 'teamsData' in response.text
        print(f"✅ Understat accessible (status {response.status_code})")
        print(f"   datesData variable: {has_dates_data}")
        print(f"   teamsData variable: {has_teams_data}")

        # Try to find JSON data
        import re
        json_pattern = r'var\s+(\w+Data)\s*=\s*JSON\.parse\('
        matches = re.findall(json_pattern, response.text)
        print(f"   JSON variables found: {matches}")
    else:
        print(f"⚠️  Understat returned status {response.status_code}")
except Exception as e:
    print(f"❌ Understat failed: {e}")

print()

# Test 3: FootyStats
print("3. Testing FootyStats.org")
try:
    url = "https://footystats.org/england/premier-league/xg"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Look for xG data
        has_xg = 'xG' in response.text or 'expected goals' in response.text.lower()
        tables = soup.find_all('table')
        print(f"✅ FootyStats accessible (status {response.status_code})")
        print(f"   xG mentions found: {has_xg}")
        print(f"   Tables found: {len(tables)}")
    else:
        print(f"⚠️  FootyStats returned status {response.status_code}")
except Exception as e:
    print(f"❌ FootyStats failed: {e}")

print()

# Test 4: StatsBomb Open Data
print("4. Testing StatsBomb Open Data (GitHub)")
try:
    url = "https://api.github.com/repos/statsbomb/open-data/contents/data"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ StatsBomb GitHub accessible")
        print(f"   Folders available: {len(data)}")
        folders = [item['name'] for item in data if item['type'] == 'dir']
        print(f"   Available: {folders[:5]}")
    else:
        print(f"⚠️  StatsBomb returned status {response.status_code}")
except Exception as e:
    print(f"❌ StatsBomb failed: {e}")

print()

# Test 5: xGstat.com
print("5. Testing xGstat.com")
try:
    url = "https://www.xgstat.com/competitions/premier-league/2024-2025/standings"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"✅ xGstat accessible (status {response.status_code})")
        print(f"   Page size: {len(response.text)} bytes")
    else:
        print(f"⚠️  xGstat returned status {response.status_code}")
except Exception as e:
    print(f"❌ xGstat failed: {e}")

print("\n=== Summary ===")
print("Sources to investigate further:")
print("1. FBref - appears to have xG data in tables")
print("2. Understat - check if JSON parsing still works")
print("3. StatsBomb - open data available on GitHub")
