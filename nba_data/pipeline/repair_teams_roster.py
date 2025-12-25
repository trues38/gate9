
import requests
import duckdb
import pandas as pd
import datetime

DB_PATH = "nba_analytics.duckdb"
# ESPN Teams endpoint
ESPN_TEAMS_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=30"

def repair_data():
    print("🚑 Repairing DIM_TEAMS & FACT_ROSTERS...")
    con = duckdb.connect(DB_PATH)
    
    # 1. FIX TEAMS (One time sync)
    print("   Fetching Teams...")
    try:
        data = requests.get(ESPN_TEAMS_URL).json()
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        
        team_rows = []
        for t in teams:
            tm = t.get("team", {})
            team_rows.append({
                "team_id": int(tm.get("id", 0)),
                "abbreviation": tm.get("abbreviation"),
                "name": tm.get("displayName"),
                "conference": "NBA",
                "division": "NBA"
            })
            
        df_teams = pd.DataFrame(team_rows)
        con.execute("CREATE TABLE IF NOT EXISTS dim_teams (team_id INTEGER PRIMARY KEY, abbreviation VARCHAR, name VARCHAR, conference VARCHAR, division VARCHAR)")
        con.execute("DELETE FROM dim_teams") 
        con.register("df_dim_teams", df_teams)
        con.execute("INSERT INTO dim_teams SELECT * FROM df_dim_teams")
        print(f"✅ Repaired {len(df_teams)} Teams in dim_teams.")
        
    except Exception as e:
        print(f"❌ Team Repair Failed: {e}")
        return

    # 2. FIX ROSTERS FOR ALL TEAMS
    print("   Fetching ALL Rosters for 30 Teams...")
    
    # Get all IDs from DB
    target_ids = con.sql(f"SELECT team_id, abbreviation FROM dim_teams").fetchall()
    
    # Validation
    if not target_ids:
        print("   No teams found in dim_teams! Aborting roster fetch.")
        return

    roster_rows = []
    
    # Counter for progress
    count = 0
    total = len(target_ids)
    
    for tid, abbr in target_ids:
        count += 1
        url_full = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tid}?enable=roster"
        try:
            # Simple Retry Logic
            resp = requests.get(url_full)
            if resp.status_code != 200:
                time.sleep(1)
                resp = requests.get(url_full)
                
            data = resp.json()
            
            # Let's try the direct roster endpoint first as it's cleaner
            url_roster = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tid}/roster"
            try:
                resp_roster = requests.get(url_roster).json()
                athletes = resp_roster.get("athletes", [])
                if not athletes:
                     athletes = resp_roster.get("team", {}).get("athletes", [])
            except:
                athletes = []
                
            # Fallback to team endpoint if roster endpoint failed
            if not athletes:
                 athletes = data.get("team", {}).get("athletes", [])

            item_count = 0
            for p in athletes:
                roster_rows.append({
                    "player_id": p.get("id"),
                    "team_id": tid,
                    "name": p.get("fullName"),
                    "status": p.get("status", {}).get("type", "Active"),
                    "updated_at": datetime.datetime.now().isoformat()
                })
                item_count += 1
            print(f"   [{count}/{total}] Fetched {item_count} players for {abbr} (ID {tid})")
            
        except Exception as e:
            print(f"   Failed roster for {abbr}: {e}")
            
    if roster_rows:
        df_roster = pd.DataFrame(roster_rows)
        
        # Schema Check & Drop to be safe (since we are doing full replaces)
        # We want to replace EVERYTHING with verified data.
        print("   ♻️  Purging old fact_rosters table to ensure clean slate...")
        con.execute("DROP TABLE IF EXISTS fact_rosters")
        con.execute("CREATE TABLE fact_rosters (player_id VARCHAR, team_id INTEGER, name VARCHAR, status VARCHAR, updated_at TIMESTAMP)")
        
        con.register("df_fresh_roster", df_roster)
        con.execute("INSERT INTO fact_rosters SELECT * FROM df_fresh_roster")
        print(f"✅ Updated {len(df_roster)} Roster entries for ALL teams.")
        
    con.close()
    
if __name__ == "__main__":
    repair_data()
