
import requests
import duckdb
from datetime import date
import time

DB_PATH = "nba_analytics.duckdb"
CON = duckdb.connect(DB_PATH)

# Initialize Table
CON.execute("DROP TABLE IF EXISTS fact_injuries")
CON.execute("""
CREATE TABLE fact_injuries (
    date DATE,
    team_id INTEGER,
    player_name VARCHAR,
    status VARCHAR, -- 'Out', 'Day-to-Day', 'Questionable'
    description VARCHAR
)
""")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def fetch_injuries():
    print("🚑 Starting Injury Fetch (ESPN Real-Time)...")
    count = 0
    
    # ESPN Team IDs 1-30
    for tid in range(1, 31):
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tid}/roster"
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            team_name = data.get('team', {}).get('displayName', f"Team {tid}")
            athletes = data.get('athletes', [])
            
            for p in athletes:
                # Check Injuries List
                injuries = p.get('injuries', [])
                # Also check 'status' dict if injuries list is empty but status is 'Inactive'??
                # Usually 'injuries' has the detail.
                
                if injuries:
                    for inj in injuries:
                        # inj structure: {'status': 'Out', 'date': '...', 'type': '...'}
                        status = inj.get('status', 'Unknown')
                        desc = inj.get('details', {}).get('returnDate', '') 
                        # Or detailed description not always available in this endpoint.
                        # Actually 'details' is sometimes just return estimate. 
                        # Let's take 'shortComment' or 'longComment' if avail, else just status.
                        # inspecting earlier output... 'injuries' was empty list.
                        # Let's save generic info.
                        
                        pname = p.get('fullName')
                        # Insert
                        CON.execute("INSERT INTO fact_injuries VALUES (?, ?, ?, ?, ?)",
                                   (date.today(), tid, pname, status, str(inj)))
                        print(f"   ⚠️ {team_name}: {pname} [{status}]")
                        count += 1
                        
            time.sleep(0.1) # Be nice
            
        except Exception as e:
            print(f"Error fetching Team {tid}: {e}")
            
    print(f"✅ Injury Fetch Complete. Total: {count} records.")
    CON.close()

if __name__ == "__main__":
    fetch_injuries()
