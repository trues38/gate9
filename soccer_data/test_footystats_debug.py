#!/usr/bin/env python3
"""
Debug FootyStats table structure
"""

import requests
from bs4 import BeautifulSoup

url = "https://footystats.org/england/premier-league/xg"
req_headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

response = requests.get(url, headers=req_headers, timeout=10)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the first table with xG
tables = soup.find_all('table')

for table in tables:
    headers_row = table.find('thead')
    if not headers_row:
        continue

    headers = [th.text.strip() for th in headers_row.find_all('th')]

    if 'xG' in headers:
        print("=== xG Table Found ===")
        print(f"Headers: {headers}\n")

        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"Total rows: {len(rows)}\n")

            # Debug first row in detail
            first_row = rows[0]
            cells = first_row.find_all('td')
            print(f"\n--- First Row Detail (Total cells: {len(cells)}) ---")

            for j, cell in enumerate(cells):
                text = cell.text.strip()
                # Only print cells that look like numbers (potential xG values)
                if text and (text.replace('.', '').isdigit() or 'xG' in text.lower()):
                    print(f"  Cell {j}: '{text}'")

        break
