#!/usr/bin/env python3
"""
Test FootyStats.org xG data parsing
"""

import requests
from bs4 import BeautifulSoup
import json

url = "https://footystats.org/england/premier-league/xg"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print("=== FootyStats xG Data Parser ===\n")

response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.text, 'html.parser')

# Method 1: Look for tables with xG data
print("Method 1: HTML Tables")
tables = soup.find_all('table')
print(f"Found {len(tables)} tables\n")

for i, table in enumerate(tables[:3]):  # Check first 3 tables
    headers_row = table.find('thead')
    if headers_row:
        headers = [th.text.strip() for th in headers_row.find_all('th')]
        if 'xG' in str(headers) or 'Expected' in str(headers):
            print(f"Table {i+1} - Headers: {headers[:8]}")  # First 8 columns

            # Get first 3 data rows
            rows = table.find('tbody').find_all('tr')[:3] if table.find('tbody') else []
            print(f"Sample rows: {len(rows)}")
            for row in rows:
                cells = [td.text.strip() for td in row.find_all('td')]
                print(f"  {cells[:5]}")  # First 5 cells
            print()

# Method 2: Look for JSON data in script tags
print("\nMethod 2: JavaScript Data")
scripts = soup.find_all('script')
for script in scripts:
    if script.string and 'xG' in script.string:
        # Try to find JSON-like structures
        text = script.string[:500]  # First 500 chars
        if '{' in text:
            print(f"Found script with xG data (preview):")
            print(f"{text[:200]}...\n")
            break

# Method 3: Look for data attributes
print("\nMethod 3: Data Attributes")
elements_with_data = soup.find_all(attrs={'data-xg': True})
if elements_with_data:
    print(f"Found {len(elements_with_data)} elements with data-xg attribute")
    for elem in elements_with_data[:3]:
        print(f"  {elem.name}: {elem.get('data-xg')}")
else:
    print("No data-xg attributes found")

# Method 4: Search for specific text patterns
print("\nMethod 4: Text Search")
if 'expected goals' in response.text.lower():
    # Count occurrences
    count = response.text.lower().count('expected goals')
    xg_count = response.text.count('xG')
    print(f"'expected goals' found: {count} times")
    print(f"'xG' found: {xg_count} times")
