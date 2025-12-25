import json
import glob
import os
import pandas as pd
from datetime import datetime

RAW_DIR = "raw"
PROCESSED_DIR = "nba_data/processed/csv"
os.makedirs(PROCESSED_DIR, exist_ok=True)

def parse_split(s):
    if s and "-" in str(s):
        parts = str(s).split("-")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return 0, 0

def process_games():
    print("📥 Processing Games...")
    files = glob.glob(os.path.join(RAW_DIR, "games", "*_games.json"))
    rows = []
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            events = data.get('events', [])
            for event in events:
                game_id = event['id']
                date_str = event['date'].split("T")[0]
                season = event.get('season', {}).get('year', 2026)
                status = event.get('status', {}).get('type', {}).get('name')
                
                competitors = event.get('competitions', [{}])[0].get('competitors', [])
                venue_id = event.get('competitions', [{}])[0].get('venue', {}).get('id', 0)
                home = next((c for c in competitors if c['homeAway']=='home'), {})
                away = next((c for c in competitors if c['homeAway']=='away'), {})
                
                if home and away:
                    rows.append({
                        "game_id": game_id,
                        "date": date_str,
                        "season": season,
                        "home_team_id": home.get('id'),
                        "home_score": home.get('score'),
                        "away_team_id": away.get('id'),
                        "away_score": away.get('score'),
                        "status": status,
                        "venue_id": int(venue_id)
                    })
        except:
            pass
            
    df = pd.DataFrame(rows)
    out_path = os.path.join(PROCESSED_DIR, "clean_games.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Saved {len(df)} games to {out_path}")

def process_boxscores():
    print("📥 Processing Boxscores...")
    files = glob.glob(os.path.join(RAW_DIR, "boxscore", "*.json"))
    rows = []
    
    # Target Columns: 20 fields (+ ids)
    # min, fgm, fga, fg_pct, tpm, tpa, tp_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, tov, stl, blk, pf, plus_minus, pts
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            box = data.get('boxscore', {})
            gid = data.get('header', {}).get('id')
            
            for tm in box.get('players', []):
                tid = tm.get('team', {}).get('id')
                # abbr = tm.get('team', {}).get('abbreviation')
                
                stats_blk = tm.get('statistics', [])
                if not stats_blk: continue
                
                for ath in stats_blk[0].get('athletes', []):
                    try:
                        stats = ath.get('stats', [])
                        if not stats: continue # DNP
                        
                        # Parse Stats
                        min_val = int(stats[0]) if stats[0]!="--" else 0
                        pts = int(stats[1])
                        fgm, fga = parse_split(stats[2])
                        tpm, tpa = parse_split(stats[3])
                        ftm, fta = parse_split(stats[4])
                        reb = int(stats[5])
                        ast = int(stats[6])
                        tov = int(stats[7])
                        stl = int(stats[8])
                        blk = int(stats[9])
                        oreb = int(stats[10]) # Verify Index!
                        dreb = int(stats[11])
                        pf = int(stats[12])
                        pm = int(stats[13])
                        
                        # Calcs
                        fg_pct = round(fgm/fga, 3) if fga else 0.0
                        tp_pct = round(tpm/tpa, 3) if tpa else 0.0
                        ft_pct = round(ftm/fta, 3) if fta else 0.0
                        
                        rows.append({
                            "game_id": gid,
                            "team_id": tid,
                            "player_id": ath.get('athlete', {}).get('id'),
                            "starter": ath.get('starter', False),
                            "min": min_val,
                            "fgm": fgm, "fga": fga, "fg_pct": fg_pct,
                            "tpm": tpm, "tpa": tpa, "tp_pct": tp_pct,
                            "ftm": ftm, "fta": fta, "ft_pct": ft_pct,
                            "oreb": oreb, "dreb": dreb, "reb": reb,
                            "ast": ast, "tov": tov, "stl": stl, "blk": blk,
                            "pf": pf, "plus_minus": pm, "pts": pts
                        })
                    except:
                        continue
        except:
            pass

    df = pd.DataFrame(rows)
    out_path = os.path.join(PROCESSED_DIR, "clean_boxscores.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Saved {len(df)} boxscores to {out_path}")
    print(f"   Columns: {list(df.columns)}")

def process_injuries():
    print("📥 Processing Injuries...")
    files = glob.glob(os.path.join(RAW_DIR, "injury", "*.json"))
    rows = []
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    rows.append({
                        "report_date": datetime.now().strftime("%Y-%m-%d"), # Approximation
                        "player_id": item.get('player_id'),
                        "team_id": item.get('team_id'),
                        "status": item.get('status'),
                        "details": item.get('details')
                    })
        except:
            pass
            
    df = pd.DataFrame(rows)
    out_path = os.path.join(PROCESSED_DIR, "clean_injuries.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Saved {len(df)} injuries to {out_path}")

if __name__ == "__main__":
    process_games()
    process_boxscores()
    process_injuries()
