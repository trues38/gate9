
import requests
import duckdb
import datetime
import pandas as pd
import json

DB_PATH = "nba_analytics.duckdb"
ESPN_SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def fetch_and_load():
    print("🚀 Fetching Layer 1 (Schedule) & Layer 7 (Odds)...")
    
    try:
        resp = requests.get(ESPN_SCOREBOARD, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return

    events = data.get("events", [])
    print(f"   Found {len(events)} games for today.")
    
    schedule_rows = []
    odds_rows = []
    
    for evt in events:
        game_id = evt.get("id")
        date_str = evt.get("date") # ISO format
        short_name = evt.get("shortName")
        location = evt.get("competitions", [{}])[0].get("venue", {}).get("fullName", "Unknown")
        
        # Competitors
        comps = evt.get("competitions", [{}])[0].get("competitors", [])
        home = next((c for c in comps if c.get("homeAway") == "home"), {})
        away = next((c for c in comps if c.get("homeAway") == "away"), {})
        
        home_team = home.get("team", {}).get("abbreviation")
        away_team = away.get("team", {}).get("abbreviation")
        
        # Layer 1: Schedule
        schedule_rows.append({
            "game_id": game_id,
            "date": date_str,
            "home_team": home_team,
            "away_team": away_team,
            "arena": location,
            "status": evt.get("status", {}).get("type", {}).get("name")
        })
        
        # Layer 7: Odds
        odds_list = evt.get("competitions", [{}])[0].get("odds", [])
        if odds_list:
            # Usually provider 'u' or similar
            # Take the first one or specific provider
            odd = odds_list[0]
            odds_rows.append({
                "game_id": game_id,
                "provider": odd.get("provider", {}).get("name", "ESPN"),
                "details": odd.get("details", ""), # e.g. "LAL -5.0"
                "over_under": odd.get("overUnder"),
                "spread": odd.get("spread"),
                "timestamp": datetime.datetime.now().isoformat()
            })
            
    # DB Operations
    con = duckdb.connect(DB_PATH)
    
    # Layer 1 Table
    con.execute("""
        CREATE TABLE IF NOT EXISTS game_schedule (
            game_id VARCHAR PRIMARY KEY,
            date VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            arena VARCHAR,
            status VARCHAR
        )
    """)
    
    # Layer 7 Table
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_odds (
            game_id VARCHAR,
            provider VARCHAR,
            details VARCHAR,
            over_under DOUBLE,
            spread DOUBLE,
            timestamp TIMESTAMP
        )
    """)
    
    # Insert Schedule (Upsert logic: Delete then insert for today's snapshot)
    if schedule_rows:
        # Check if game_ids exist to avoid dupes? Or just DELETE for simplicity since it's a "Light Fetch"
        con.execute("DELETE FROM game_schedule WHERE game_id IN (" + ",".join([f"'{r['game_id']}'" for r in schedule_rows]) + ")")
        
        df_sched = pd.DataFrame(schedule_rows)
        con.register("df_sched", df_sched)
        con.execute("INSERT INTO game_schedule SELECT * FROM df_sched")
        print(f"✅ Layer 1: Inserted {len(df_sched)} games into 'game_schedule'.")
    else:
        print("⚠️ No games found for Layer 1.")
        
    # Insert Odds
    if odds_rows:
        df_odds = pd.DataFrame(odds_rows)
        con.register("df_odds", df_odds)
        con.execute("INSERT INTO market_odds SELECT * FROM df_odds")
        print(f"✅ Layer 7: Inserted {len(df_odds)} odds records into 'market_odds'.")
    else:
        print("⚠️ No odds found (~Offseason or Pre-market?). Layer 7 empty.")
        
    con.close()

if __name__ == "__main__":
    fetch_and_load()
