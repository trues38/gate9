#!/usr/bin/env python3
"""
Detailed FootyStats.org xG data extraction
"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://footystats.org/england/premier-league/xg"
req_headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print("=== Detailed FootyStats xG Extraction ===\n")

response = requests.get(url, headers=req_headers, timeout=10)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the main xG table
tables = soup.find_all('table')

for i, table in enumerate(tables):
    # Check if this is the xG table
    headers_row = table.find('thead')
    if not headers_row:
        continue

    headers = [th.text.strip() for th in headers_row.find_all('th')]

    # Look for xG column
    if 'xG' in headers:
        print(f"Found xG table (Table #{i+1})")
        print(f"Headers: {headers}\n")

        # Find xG column index
        try:
            xg_idx = headers.index('xG')
            xga_idx = headers.index('xGA') if 'xGA' in headers else None
            xgd_idx = headers.index('xGD') if 'xGD' in headers else None

            print(f"Column indices - xG: {xg_idx}, xGA: {xga_idx}, xGD: {xgd_idx}\n")
        except:
            print("Could not find xG column index")
            continue

        # Extract data rows
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"Found {len(rows)} data rows\n")

            xg_data = []
            for row in rows[:10]:  # First 10 teams
                cells = row.find_all('td')
                if len(cells) > max(xg_idx, xga_idx or 0, xgd_idx or 0):
                    # Extract team name from link if available
                    team_cell = cells[2] if len(cells) > 2 else cells[0]
                    team_link = team_cell.find('a')
                    if team_link:
                        team_name = team_link.text.strip()
                    else:
                        team_name = team_cell.text.strip()

                    # Clean team name (remove extra text like "FC", league position, etc.)
                    team_name = re.split(r'(Form|League|Premier|Matches|Played)', team_name)[0].strip()
                    team_name = re.sub(r'FC$', '', team_name).strip()
                    team_name = re.sub(r'\s+', ' ', team_name)

                    xg = cells[xg_idx].text.strip()
                    xga = cells[xga_idx].text.strip() if xga_idx else 'N/A'
                    xgd = cells[xgd_idx].text.strip() if xgd_idx else 'N/A'

                    # Skip if xG is not a number
                    if not re.match(r'^[\d.]+$', xg):
                        continue

                    xg_data.append({
                        'team': team_name,
                        'xG': xg,
                        'xGA': xga,
                        'xGD': xgd
                    })

                    print(f"{team_name:30s} xG: {xg:6s} xGA: {xga:6s} xGD: {xgd:6s}")

            print(f"\n✅ Successfully extracted {len(xg_data)} teams' xG data")
            break

# Test if we can get match-level data
print("\n=== Testing Match-Level xG ===")
match_url = "https://footystats.org/england/premier-league"
response = requests.get(match_url, headers=req_headers, timeout=10)

if 'xG' in response.text:
    print("✅ Match pages also contain xG data")
    # Count xG occurrences
    xg_count = response.text.count('xG')
    print(f"   Found {xg_count} xG mentions on match page")
else:
    print("❌ No xG data on match pages")
