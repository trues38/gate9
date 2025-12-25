
import duckdb
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from openai import OpenAI

# CONFIG
DB_PATH = "nba_analytics.duckdb"
BACKTEST_DIR = "backtest/reports"
SNAPSHOT_DIR = "backtest/snapshots"
load_dotenv("/Users/js/g9/.env")

# Ensure Dirs
os.makedirs(BACKTEST_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

STARS = [
    # TOR/NYK
    "Scottie Barnes", "RJ Barrett", "Immanuel Quickley", "Gradey Dick", "Jakob Poeltl",
    "Jalen Brunson", "Karl-Anthony Towns", "Mikal Bridges", "OG Anunoby", "Josh Hart",
    # MIA/ORL
    "Jimmy Butler", "Bam Adebayo", "Tyler Herro", "Terry Rozier", "Jaime Jaquez Jr.",
    "Paolo Banchero", "Franz Wagner", "Jalen Suggs", "Wendell Carter Jr.", "Cole Anthony",
    # LEAGUE WIDE (Partial List)
    "LeBron James", "Anthony Davis", "Stephen Curry", "Luka Doncic", "Kyrie Irving",
    "Nikola Jokic", "Jamal Murray", "Shai Gilgeous-Alexander", "Chet Holmgren",
    "Kevin Durant", "Devin Booker", "Anthony Edwards", "Rudy Gobert", "Victor Wembanyama",
    "Jayson Tatum", "Jaylen Brown", "Giannis Antetokounmpo", "Damian Lillard",
    "Joel Embiid", "Tyrese Maxey", "Donovan Mitchell", "Trae Young"
]

def build_backtest_snapshot(game, target_date):
    """
    Builds a JSON snapshot using ONLY data from BEFORE target_date.
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    gid = game[0]
    h_team = game[2]
    a_team = game[3]
    h_id = 0 # Need ID lookup
    a_id = 0 
    
    # Team ID Lookup (Hardcoded Map for robust testing)
    # Ideally should be a DB join, but simplified for this script
    TEAM_MAP = {
        "MIA": 14, "ORL": 19, "NYK": 18, "NY": 18, "TOR": 28, "BOS": 2, "PHI": 20, "MIL": 15, "CLE": 5,
        "LAL": 13, "GSW": 9, "GS": 9, "PHX": 21, "SAC": 23, "DEN": 7, "MIN": 16, "OKC": 25, "POR": 22, "UTA": 26, "UTAH": 26, "LAC": 12,
        "DAL": 6, "HOU": 10, "MEM": 29, "NOP": 17, "NO": 17, "SAS": 24, "SA": 24, "ATL": 1, "CHA": 30, "WAS": 27, "WSH": 27, "DET": 8, "IND": 11, "CHI": 4, "BKN": 3
    }
    h_id = TEAM_MAP.get(h_team, 0)
    a_id = TEAM_MAP.get(a_team, 0)

    # 1. Team Regimes (Strictly BEFORE target_date)
    # Example: If game is 12-01, we want max date < '2025-12-01'
    def get_regime(tid):
        q = f"""
        SELECT momentum_score, volatility_score, regime_label 
        FROM fact_regimes 
        WHERE team_id={tid} AND date < '{target_date}' 
        ORDER BY date DESC LIMIT 1
        """
        res = con.sql(q).fetchone()
        if res: return {"momentum": float(res[0]), "volatility": float(res[1]), "label": res[2]}
        return {"momentum": 0.0, "volatility": 0.0, "label": "Unknown"}
    
    h_reg = get_regime(h_id)
    a_reg = get_regime(a_id)
    
    # 2. Injuries (Mock Logic for Backtest - Assume we don't have accurate historical injury daily logs yet)
    # We will assume "Healthy" if no specific historical injury table exists.
    # User said: "Day-by-Day... Injury(전날까지) 적용"
    # If fact_injuries is real-time only, we can't backtest injury effectively without a history table.
    # We will return empty list but log this limitation.
    h_out = []
    a_out = []
    
    # 3. Player Regimes (Dynamic Calculation from Boxscores)
    
    def get_player_dna(pid, p_name):
        # Fetch last 5 games stats before target_date
        q = f"""
        SELECT pts, plus_minus
        FROM fact_boxscores 
        WHERE player_id={pid} AND game_date < '{target_date}'
        ORDER BY game_date DESC LIMIT 5
        """
        try:
            rows = con.sql(q).fetchall()
        except: return None
        
        if not rows: return None
        
        # Simple Momentum Logic
        total_pts = sum([r[0] for r in rows])
        avg_pts = total_pts / len(rows)
        
        # Trend: Compare Last 2 vs Avg?
        recent_pts = rows[0][0] if rows else 0
        trend_val = recent_pts - avg_pts
        trend_str = "Surging" if trend_val > 5 else "Slumping" if trend_val < -5 else "Stable"
        
        return {
            "name": p_name,
            "momentum": round(avg_pts, 1), # Using Avg PTS as simplistic momentum for now
            "trend": trend_str,
            "last_5_avg": round(avg_pts, 1)
        }

    h_players = []
    a_players = []
    
    # Fill Top Players
    for team_id_chk, list_ref in [(h_id, h_players), (a_id, a_players)]:
        if team_id_chk == 0: continue
        try:
             # Identify Top 5 Scorers for this team historically
             q_top = f"""
             SELECT player_id, name, AVG(pts) as ppg
             FROM fact_boxscores 
             WHERE team_id={team_id_chk} AND game_date < '{target_date}'
             GROUP BY player_id, name
             ORDER BY ppg DESC
             LIMIT 5
             """
             top_pl = con.sql(q_top).fetchall()
             
             for p_row in top_pl:
                 dna = get_player_dna(p_row[0], p_row[1])
                 if dna: list_ref.append(dna)
        except Exception as e:
             print(f"Player Reg Error for {team_id_chk}: {e}")
             pass
    
    # 4. Narratives (Strictly BEFORE target_date)
    # stories_raw files have timestamps?
    # I'll enable a basic "News Search" but filter by file mod time? Hard to do perfectly.
    # I will use "Generic" for backtest to be safe.
    
    game_obj = {
        "game_id": gid,
        "date": str(target_date),
        "teams": {"home": h_team, "away": a_team},
        "team_regimes": {h_team: h_reg, a_team: a_reg},
        "player_regimes": {h_team: h_players, a_team: a_players},
        "injuries": {h_team: h_out, a_team: a_out},
        "referees": [], # No historical ref data
        "news_narrative": {h_team: "Backtest Mode: News Hidden", a_team: "Backtest Mode: News Hidden"}
    }
    con.close()
    return game_obj

def run_backtest_day(target_date):
    print(f"\n📅 REPLAYING: {target_date}...")
    con = duckdb.connect(DB_PATH, read_only=True)
    
    # Get Games for this Day
    games = con.sql(f"SELECT * FROM fact_game_results WHERE game_date = '{target_date}'").fetchall()
    con.close()
    
    if not games:
        print("  -> No games found.")
        return []
        
    results = []
    
    report_header = f"""# DAILY REGIME REPORT: {target_date}
**Protocol**: Replay Mode (Strict History Isolation)
**Games**: {len(games)}
---
"""
    day_report_content = ""

    for g in games:
        snapshot = build_backtest_snapshot(g, target_date)
        
        # Save Snapshot
        s_path = f"{SNAPSHOT_DIR}/{target_date}_{g[2]}_{g[3]}.json"
        with open(s_path, "w") as f:
            json.dump(snapshot, f, indent=2)
            
        # Analysis (Layer 4 Model)
        hmom = snapshot['team_regimes'][g[2]]['momentum']
        amom = snapshot['team_regimes'][g[3]]['momentum']
        hvol = snapshot['team_regimes'][g[2]]['volatility']
        avol = snapshot['team_regimes'][g[3]]['volatility']
        
        predicted_spread = 2.5 + ((hmom - amom) * 5.0)
        
        # Actual Result
        # g indices: 0:gid, 1:date, 2:h, 3:a, 4:hs, 5:as, 6:spread...
        actual_spread = g[6] # closing_spread
        home_score = g[4]
        away_score = g[5]
        diff = home_score - away_score
        
        row = {
            "date": str(target_date),
            "matchup": f"{g[3]} @ {g[2]}",
            "model_spread": round(predicted_spread, 1),
            "actual_diff": diff,
            "casino_spread": actual_spread,
            "error": abs(diff - predicted_spread)
        }
        results.append(row)
        
        # Aggregate Report Content
        # Check regime label existence
        h_label = snapshot['team_regimes'][g[2]].get('label', 'Unknown')
        a_label = snapshot['team_regimes'][g[3]].get('label', 'Unknown')
        
        # Player DNA Strings
        h_dna = ", ".join([f"{p['name']} ({p['trend']} {p['momentum']})" for p in snapshot['player_regimes'][g[2]][:3]])
        a_dna = ", ".join([f"{p['name']} ({p['trend']} {p['momentum']})" for p in snapshot['player_regimes'][g[3]][:3]])

        day_report_content += f"""
## {g[3]} @ {g[2]}
- **Regimes**: {g[2]} ({h_label} {hmom:.2f}), {g[3]} ({a_label} {amom:.2f})
- **Key Players**:
  - **{g[2]}**: {h_dna}
  - **{g[3]}**: {a_dna}
- **Prediction**: {g[2]} {predicted_spread:+.1f}
- **Actual**: {home_score}-{away_score} (Diff {diff}, Spread {actual_spread})
- **Error**: {abs(diff - predicted_spread):.1f}
- **Result**: {"✅ Win" if abs(diff - predicted_spread) < abs(diff - actual_spread) else "❌ Loss"} (vs Market)

"""

    # Save Day Report
    r_path = f"{BACKTEST_DIR}/{target_date}.md"
    with open(r_path, "w") as f:
        f.write(report_header + day_report_content)
            
    return results

if __name__ == "__main__":
    start_date = date(2025, 12, 1) # Refresh Stale Reports
    end_date = date(2025, 12, 10) # Full Sweep
    
    current = start_date
    all_results = []
    
    while current <= end_date:
        res = run_backtest_day(current)
        all_results.extend(res)
        current += timedelta(days=1)
        
    print(f"\\n✅ Replay Backtest #1 Complete")
    
    # Save Accuracy Table
    if all_results:
        df = pd.DataFrame(all_results)
        df.to_csv("backtest/accuracy_table.csv", index=False)
        print("Saved backtest/accuracy_table.csv")
        try:
            print(df.describe())
        except: pass
    else:
        print("No results found.")
