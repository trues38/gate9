
import requests
import json
import duckdb
from datetime import date, timedelta
import os

# CONFIG
DB_PATH = "nba_analytics.duckdb"
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)

def calculate_new_momentum(current_score, point_differential, is_win):
    """
    Simple Momentum Algorithm V1
    - Win: +0.2 + (Margin / 20)
    - Loss: -0.2 - (Margin / 20)
    - Decay: Previous score * 0.9 (Recency Bias)
    """
    decayed = current_score * 0.9
    
    impact = 0.0
    if is_win:
        impact = 0.2 + (abs(point_differential) / 20.0)
    else:
        impact = -0.2 - (abs(point_differential) / 20.0)
        
    return round(decayed + impact, 2)

def determine_label(score):
    if score > 1.0: return "Juggernaut"
    if score > 0.4: return "Surging"
    if score > -0.4: return "Balanced"
    if score > -1.0: return "Slumping"
    return "Crisis"

def update_daily_regimes():
    print(f"🔄 Running Daily Regime Update for {YESTERDAY} -> {TODAY}...")
    
    con = duckdb.connect(DB_PATH)
    
    # 1. Fetch Completed Games for YESTERDAY
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={YESTERDAY.strftime('%Y%m%d')}"
    print(f"   Fetching Results from: {url}")
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        events = data.get('events', [])
    except Exception as e:
        print(f"❌ API Error: {e}")
        return

    print(f"   Found {len(events)} games.")
    
    updates = []
    
    for event in events:
        status = event['status']['type']['state']
        if status != 'post': continue
        
        # Parse Result
        competitions = event['competitions'][0]
        competitors = competitions['competitors']
        
        home = next(c for c in competitors if c['homeAway'] == 'home')
        away = next(c for c in competitors if c['homeAway'] == 'away')
        
        home_score = int(home['score'])
        away_score = int(away['score'])
        margin = home_score - away_score
        
        updates.append({
            "team_id": int(home['id']),
            "is_win": margin > 0,
            "margin": margin
        })
        updates.append({
            "team_id": int(away['id']),
            "is_win": margin < 0,
            "margin": -margin # Perspective of away team
        })

    # 2. Update Regimes in DuckDB
    print(f"   Updating {len(updates)} teams...")
    
    for u in updates:
        tid = u['team_id']
        
        # Get Current/Previous Score from DB
        # Look for TODAY first (if re-running), else look for yesterday/latest
        # "LATEST" logic: Order by date desc limit 1
        res = con.execute(f"SELECT momentum_score, volatility_score FROM fact_regimes WHERE team_id = {tid} ORDER BY date DESC LIMIT 1").fetchone()
        
        if res:
            curr_mom, curr_vol = res
        else:
            curr_mom, curr_vol = 0.0, 0.0 # Default
            
        # Calculate New
        new_mom = calculate_new_momentum(curr_mom, u['margin'], u['is_win'])
        new_vol = round((curr_vol * 0.9) + (abs(u['margin']) / 100.0), 2) # Volatility update
        new_label = determine_label(new_mom)
        
        # Insert New Snapshot for TODAY
        # Delete if exists to allow re-runs
        con.execute(f"DELETE FROM fact_regimes WHERE team_id = {tid} AND date = '{TODAY}'")
        
        con.execute("""
            INSERT INTO fact_regimes (date, team_id, momentum_score, volatility_score, regime_label, record, streak)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (TODAY, tid, new_mom, new_vol, new_label, 'Synced', 'Active'))
        
        print(f"   ✅ Team {tid}: {curr_mom} -> {new_mom} ({new_label})")
        
    con.close()
    print("💾 Daily Update Complete.")

if __name__ == "__main__":
    update_daily_regimes()
