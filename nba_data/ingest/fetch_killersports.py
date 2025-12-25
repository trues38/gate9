import requests
import pandas as pd
import os
import json

# SDQL API Endpoint
# Ref: https://killersports.com/sdql_api
URL = "http://api.killersports.com/sdql"

# Query provided by User:
# date, team, opponent, line, site, margin @ season=2024 and site=home
# Note: season=2024 means the 2024-25 season (Current).
SDQL_QUERY = "date, team, opponent, line, site, margin @ season=2024 and site=home"

OUTPUT_FILE = "processed/odds_2025_raw.csv"

def fetch_qs_odds():
    print(f"🚀 Fetching 2025 Odds from KillerSports...")
    print(f"   Query: {SDQL_QUERY}")
    
    params = {
        'sdql': SDQL_QUERY,
        'output': 'json'
    }
    
    try:
        r = requests.get(URL, params=params)
        r.raise_for_status()
        
        data = r.json()
        
        # Structure: {'headers': [...], 'groups': [{'columns': [[val1, val2...], [val1...]]}]}
        # Usually it's simpler lists if no grouping.
        # Let's inspect structure if strict list of dicts isn't returned.
        
        headers = data.get('headers')
        rows = data.get('groups', [])[0].get('columns', [])
        
        # Columns is list of lists (Column-oriented?)
        # Let's verify.
        # Usually SDQL JSON output is: headers: [A, B], groups: [{columns: [[row1_A, row2_A...], [row1_B, row2_B...]]}]
        # It's Columnar!
        
        if not rows:
            print("⚠️ No data returned.")
            return

        # Convert Columnar to Row-wise
        # rows[0] is list of all Dates
        # rows[1] is list of all Teams
        df_dict = {}
        for idx, col_name in enumerate(headers):
            df_dict[col_name] = rows[idx]
            
        df = pd.DataFrame(df_dict)
        
        print(f"✅ Fetched {len(df)} games.")
        print(df.head())
        
        # Save
        os.makedirs("processed", exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"💾 Saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ Error fetching from KillerSports: {e}")
        # Identify if blocked
        if "403" in str(e) or "429" in str(e):
            print("   (Access might be blocked. Manual download required.)")

if __name__ == "__main__":
    fetch_qs_odds()
