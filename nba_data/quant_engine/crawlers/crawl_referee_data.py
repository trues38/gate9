import requests
from bs4 import BeautifulSoup
import json
import os
import datetime

# Configuration
RAW_REF_DIR = "raw/referee"
os.makedirs(RAW_REF_DIR, exist_ok=True)

# URL for CURRENT Season (2024-25 -> 'NBA_2025_refs.html')
URL = "https://www.basketball-reference.com/referees/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def fetch_referee_stats():
    print(f"👔 Fetching Referee Data from {URL}...")
    try:
        resp = requests.get(URL, headers=HEADERS)
        if resp.status_code == 404:
            # Fallback to 2024 if 2025 not avail?
            print("⚠️ 2025 Refs not found, trying 2024...")
            fallback_url = "https://www.basketball-reference.com/leagues/NBA_2024_refs.html"
            resp = requests.get(fallback_url, headers=HEADERS)
            
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        table = soup.find("table", {"id": "referees"})
        
        if not table:
            print("❌ Could not find #referees table")
            return

        refs_data = []
        tbody = table.find("tbody")
        rows = tbody.find_all("tr")
        
        for row in rows:
            # Skip header repeats
            if row.get("class") and "thead" in row.get("class"):
                continue
                
            cols = row.find_all(["th", "td"])
            if not cols: continue
            
            # Columns (Approx):
            # 0: Rank/Name? Usually Name is th or first td.
            # Let's inspect typical structure: 
            # Referee, G, ...
            
            # BBRef usually puts the Key in 'th' (scope=row)
            ref_name = cols[0].text.strip()
            
            # Check if it's a valid row
            if not ref_name or ref_name == "Referee": continue
            
            # Extract data safely (by data-stat if possible, or index)
            # Using data-stat attribute is safer
            def get_val(stat_name):
                cell = row.find("td", {"data-stat": stat_name})
                return cell.text.strip() if cell else None
            
            data_point = {
                "name": ref_name,
                "games": get_val("g"),
                "fga_per_game": get_val("fga_ per_g"),
                "fta_per_game": get_val("fta_per_g"),
                "pf_per_game": get_val("pf_per_g"),
                "pts_per_game": get_val("pts_per_g"),
                "home_win_pct": get_val("home_win_percentage"),
                "foul_pct_home": get_val("pf_per_g_home"), # Note: might vary
                "foul_pct_visitor": get_val("pf_per_g_visitor")
            }
            refs_data.append(data_point)
            
        # Save
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        filepath = os.path.join(RAW_REF_DIR, f"{today_str}_referees.json")
        
        with open(filepath, "w") as f:
            json.dump(refs_data, f, indent=2)
            
        print(f"✅ Saved {len(refs_data)} referees to {filepath}")
        
    except Exception as e:
        print(f"❌ Error fetching refs: {e}")

if __name__ == "__main__":
    fetch_referee_stats()
