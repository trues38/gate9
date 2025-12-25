
import duckdb
from datetime import date, timedelta, datetime

DB_PATH = "nba_analytics.duckdb"

def calculate_momentum(history_games, team_name):
    """
    Calc Momentum from last 5 games history
    Each game dict: {margin: int, is_win: bool}
    """
    score = 0.0
    # Simple algorithm: Moving Average of Margin? Or Weighted?
    # Engine V3 Logic:
    # Win: +0.2 + (Margin/20)
    # Loss: -0.2 - (Margin/20)
    # Decay: 0.9
    
    # We need to simulate the day-by-day evolution.
    # But for 'bulk' recompute, we can just take the last 5 games relative to Target Date.
    
    # Sort by date ascending
    sorted_games = sorted(history_games, key=lambda x: x['date'])
    
    current_score = 0.0
    current_vol = 0.0
    
    for g in sorted_games:
        margin = g['margin']
        is_win = margin > 0
        
        # Momentum
        decayed = current_score * 0.9
        impact = 0.0
        if is_win:
            impact = 0.2 + (abs(margin) / 20.0)
        else:
            impact = -0.2 - (abs(margin) / 20.0)
        current_score = round(decayed + impact, 2)
        
        # Volatility
        current_vol = round((current_vol * 0.9) + (abs(margin) / 100.0), 2)

    return current_score, current_vol

def get_label(score):
    if score > 1.0: return "Juggernaut"
    if score > 0.4: return "Surging"
    if score > -0.4: return "Balanced"
    if score > -1.0: return "Slumping"
    return "Crisis"

def run_recalc():
    con = duckdb.connect(DB_PATH)
    
    start = date(2025, 10, 22)
    end = date(2025, 12, 10)
    
    curr = start
    while curr <= end:
        print(f"🔄 Recalculating Regimes for {curr}...")
        
        # for each team...
        # We need all team IDs or names.
        # Get list of teams played so far or from raw data
        teams = con.sql("SELECT DISTINCT home_team, away_team FROM fact_game_results").fetchall()
        team_set = set()
        for t in teams:
            team_set.add(t[0])
            team_set.add(t[1])
            
        for team_abbr in team_set:
            # Fetch games BEFORE curr
            # We need Team ID usually. Just use Abbr for now if DB allows, but schema says team_id int.
            # We need map.
            # Lazy map:
            # Get ID from fact_game_results? No it has ABBR. 
            # Fact_regimes needs ID.
            # Let's map Abbr -> ID using a query if possible or hardcode map again.
            # Actually fact_game_results doesn't have ID.
            # We must update `fact_game_results` to include IDs or use a Map.
            
            # Using simple hardcoded map for safety in this script
            TEAM_MAP = {
                "MIA": 14, "ORL": 19, "NYK": 18, "NY": 18, "TOR": 28, "BOS": 2, "PHI": 20, "MIL": 15, "CLE": 5,
                "LAL": 13, "GSW": 9, "GS": 9, "PHX": 21, "SAC": 23, "DEN": 7, "MIN": 16, "OKC": 25, "POR": 22, "UTA": 26, "UTAH": 26, "LAC": 12,
                "DAL": 6, "HOU": 10, "MEM": 29, "NOP": 17, "NO": 17, "SAS": 24, "SA": 24, "ATL": 1, "CHA": 30, "WAS": 27, "WSH": 27, "DET": 8, "IND": 11, "CHI": 4, "BKN": 3
            }
            tid = TEAM_MAP.get(team_abbr, 0)
            if tid == 0: continue
            
            # Fetch Games involving this team before Date
            # home or away
            q = f"""
            SELECT game_date, home_team, away_team, home_score, away_score 
            FROM fact_game_results 
            WHERE (home_team='{team_abbr}' OR away_team='{team_abbr}') 
            AND game_date < '{curr}'
            ORDER BY game_date ASC
            """
            games = con.sql(q).fetchall()
            
            history = []
            for g in games:
                is_home = (g[1] == team_abbr)
                margin = (g[3] - g[4]) if is_home else (g[4] - g[3])
                history.append({"date": g[0], "margin": margin})
            
            if not history: continue
            
            mom, vol = calculate_momentum(history, team_abbr)
            label = get_label(mom)
            
            # Insert into fact_regimes
            con.execute(f"DELETE FROM fact_regimes WHERE team_id={tid} AND date='{curr}'")
            con.execute("""
                INSERT INTO fact_regimes (date, team_id, momentum_score, volatility_score, regime_label, record, streak)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (curr, tid, mom, vol, label, 'Backfilled', 'Active'))
        
        curr += timedelta(days=1)
            
    con.close()
    print("✅ Recalculation Complete.")

if __name__ == "__main__":
    run_recalc()
