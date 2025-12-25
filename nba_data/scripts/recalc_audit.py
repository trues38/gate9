import pandas as pd
import numpy as np

LOG_PATH = "g9_core_export/REPORTS/audit_llm_log.csv"
ODDS_PATH = "g9_core_export/DATA/nba_2008-2025.csv"

def grade_bet_corrected(record, action, odds_df):
    if action == "PASS": return 0.0
    
    # Simple Date/Team lookup
    # Need to reconstruct lookup logic or just load mapped
    # Since we have PnL in log, we can deduce result? No.
    # We need to re-grade.
    
    timestamp = pd.to_datetime(record['date'])
    mapping_rev = {
        'atl': 'ATLANTA HAWKS', 'bos': 'BOSTON CELTICS', 'bkn': 'BROOKLYN NETS', 'cha': 'CHARLOTTE HORNETS', 'chi': 'CHICAGO BULLS', 'cle': 'CLEVELAND CAVALIERS', 'dal': 'DALLAS MAVERICKS', 'den': 'DENVER NUGGETS', 'det': 'DETROIT PISTONS', 'gsw': 'GOLDEN STATE WARRIORS', 'hou': 'HOUSTON ROCKETS', 'ind': 'INDIANA PACERS', 'lac': 'LA CLIPPERS', 'lal': 'LOS ANGELES LAKERS', 'mem': 'MEMPHIS GRIZZLIES', 'mia': 'MIAMI HEAT', 'mil': 'MILWAUKEE BUCKS', 'min': 'MINNESOTA TIMBERWOLVES', 'nop': 'NEW ORLEANS PELICANS', 'nyk': 'NEW YORK KNICKS', 'okc': 'OKLAHOMA CITY THUNDER', 'orl': 'ORLANDO MAGIC', 'phi': 'PHILADELPHIA 76ERS', 'phx': 'PHOENIX SUNS', 'por': 'PORTLAND TRAIL BLAZERS', 'sac': 'SACRAMENTO KINGS', 'sas': 'SAN ANTONIO SPURS', 'tor': 'TORONTO RAPTORS', 'uta': 'UTAH JAZZ', 'was': 'WASHINGTON WIZARDS'
    }
    team_to_code = {v: k for k, v in mapping_rev.items()}
    code = team_to_code.get(record['team_name']) # CSV has joined id usually?
    # CSV cols: id,pred_regime,true_regime,confidence,action,pnl,odds_copy,reason
    # ID is "20231024_DENVER NUGGETS"
    
    id_parts = record['id'].split('_')
    date_str = id_parts[0] # 20231024
    team_name = id_parts[1]
    
    code = team_to_code.get(team_name)
    if not code: return 0.0
    
    # Lookup Odds
    day_games = odds_df[odds_df['date'] == pd.to_datetime(date_str, format='%Y%m%d')]
    if day_games.empty: return 0.0
    
    game = day_games[(day_games['home'] == code) | (day_games['away'] == code)]
    if game.empty: return 0.0
    game = game.iloc[0]
    
    score_home = game['score_home']
    score_away = game['score_away']
    spread = game['spread']
    total_line = game['total']
    fav_team = game['whos_favored']
    
    pnl = 0.0
    
    if action == "UNDER":
        if (score_home + score_away) < total_line: pnl = 0.9
        else: pnl = -1.0
        
    elif action == "FAV_SPREAD":
        is_home = (game['home'] == code)
        is_fav = (is_home and fav_team == 'home') or (not is_home and fav_team == 'away')
        
        # Original Pilot Logic: Bet ON Team if they are Fav?
        # "Favorite_Hold" regime -> Implies they cover.
        if is_fav:
            covered = False
            if is_home:
                if (score_home - score_away) > spread: covered = True
            else:
                if (score_away - score_home) > spread: covered = True
            
            if covered: pnl = 0.9
            else: pnl = -1.0
        else:
            # Regime is FavHold but Team is Dog? Contradiction. Pass.
            pnl = 0.0
            
    elif action == "DOG_SPREAD": # Only for Underdog Regime
         # Same as before
         pass

    return pnl

def recalc():
    df = pd.read_csv(LOG_PATH)
    odds = pd.read_csv(ODDS_PATH)
    odds['date'] = pd.to_datetime(odds['date'])
    
    new_results = []
    
    for idx, row in df.iterrows():
        regime = row['pred_regime']
        
        # PILOT LOGIC MAPPING
        # Grind -> UNDER
        # Favorite_Hold -> FAV_SPREAD (Corrected)
        # Favorite_Collapse -> FADE_FAV (Wait, simpler just check Hold)
        
        action = "PASS"
        if "Grind" in regime:
            # Add Range Filter? User Audit asked for Range.
            # Let's keep User's Range filter but FLIP the Action for FavHold.
            action = "UNDER" 
            # We don't have Total in CSV to check range strictly here without lookup.
            # Assuming we apply Pilot Logic (No range or User Range).
            # Let's apply Pilot Logic (No Range) first to see if direction is right.
            
        elif "Favorite_Hold" in regime:
            action = "FAV_SPREAD" # FLIPPED FROM DOG_SPREAD
            
        # Re-grade
        # Need to reconstruct record dict for grade_bet func
        parts = row['id'].split('_')
        record = {'id': row['id'], 'date': parts[0], 'team_name': parts[1]}
        
        pnl = grade_bet_corrected(record, action, odds)
        new_results.append(pnl)
        
    df['pnl_corrected'] = new_results
    
    bets = df[df['pnl_corrected'] != 0.0]
    roi = bets['pnl_corrected'].sum() / len(bets) * 100 if len(bets) > 0 else 0.0
    
    print(f"Original ROI: {df[df['action']!='PASS']['pnl'].mean()*100:.2f}%")
    print(f"Corrected ROI (FavHold->FavSpread): {roi:.2f}% (Bets: {len(bets)})")

if __name__ == "__main__":
    recalc()
