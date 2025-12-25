import pandas as pd
import numpy as np
import itertools
from lab_cause_regime import load_data, tag_causes, get_odds_game

OUTPUT_REPORT = "g9_core_export/REPORTS/lab_situation_catalog.md"

def calc_roi(bet_count, profit_u):
    if bet_count == 0: return 0.0
    return (profit_u / bet_count * 100)

def get_market_buckets(game):
    # Spread Bin
    s_bin = "S_UNK"
    spread = game['spread']
    if spread <= 3.5: s_bin = "S1(0-3.5)"
    elif spread <= 7.5: s_bin = "S2(4-7.5)"
    else: s_bin = "S3(8+)"
    
    # Total Bin
    t_bin = "T_UNK"
    total = game['total']
    if total < 215: t_bin = "T1(<215)"
    elif total <= 235: t_bin = "T2(215-235)"
    else: t_bin = "T3(>235)"
    
    # Fav Home
    fav_home = (game['whos_favored'] == 'home')
    
    return s_bin, t_bin, fav_home

def run_mining():
    print("Loading Data for Mining...")
    df, odds, regimes = load_data()
    
    # Prepare Lookup
    mapping_rev = {
        'atl': 'ATLANTA HAWKS', 'bos': 'BOSTON CELTICS', 'bkn': 'BROOKLYN NETS', 'cha': 'CHARLOTTE HORNETS', 'chi': 'CHICAGO BULLS', 'cle': 'CLEVELAND CAVALIERS', 'dal': 'DALLAS MAVERICKS', 'den': 'DENVER NUGGETS', 'det': 'DETROIT PISTONS', 'gsw': 'GOLDEN STATE WARRIORS', 'hou': 'HOUSTON ROCKETS', 'ind': 'INDIANA PACERS', 'lac': 'LA CLIPPERS', 'lal': 'LOS ANGELES LAKERS', 'mem': 'MEMPHIS GRIZZLIES', 'mia': 'MIAMI HEAT', 'mil': 'MILWAUKEE BUCKS', 'min': 'MINNESOTA TIMBERWOLVES', 'nop': 'NEW ORLEANS PELICANS', 'nyk': 'NEW YORK KNICKS', 'okc': 'OKLAHOMA CITY THUNDER', 'orl': 'ORLANDO MAGIC', 'phi': 'PHILADELPHIA 76ERS', 'phx': 'PHOENIX SUNS', 'por': 'PORTLAND TRAIL BLAZERS', 'sac': 'SACRAMENTO KINGS', 'sas': 'SAN ANTONIO SPURS', 'tor': 'TORONTO RAPTORS', 'uta': 'UTAH JAZZ', 'was': 'WASHINGTON WIZARDS'
    }
    team_to_code = {v: k for k, v in mapping_rev.items()}
    
    odds_lookup = {}
    for idx, row in odds.iterrows():
        home_name = mapping_rev.get(row['home'], 'UNKNOWN')
        away_name = mapping_rev.get(row['away'], 'UNKNOWN')
        odds_lookup[(row['date'], home_name)] = row
        odds_lookup[(row['date'], away_name)] = row
        
    # Tag Causes
    df = tag_causes(df, odds_lookup, team_to_code)
    
    # Expand Market State
    market_states = []
    valid_rows = []
    
    print("Expanding Market States...")
    for idx, row in df.iterrows():
        game = odds_lookup.get((row['Date'], row['Team']))
        if game is None: continue
        
        s_bin, t_bin, fav_home = get_market_buckets(game)
        
        # We need to associate Bets here to avoid recalculating later
        # Calculate Bet Outcomes Once
        is_home_team = (game['home'] == team_to_code.get(row['Team'].lower()))
        fav_team = game['whos_favored']
        spread = game['spread'] # always positive
        score_diff = game['score_home'] - game['score_away']
        total_score = game['score_home'] + game['score_away']
        
        # Fav Cover Check
        fav_covered = False
        if fav_team == 'home':
             if score_diff > spread: fav_covered = True
        else:
             if score_diff < -spread: fav_covered = True
             
        # Result for THIS ROW's Perspective? 
        # Standard: Look for "Fav Cover", "Dog Cover", "Over", "Under" as global properties of the game.
        # But Filter is (Cause for THIS TEAM).
        # So we group by (Team Cause) -> (Game Result).
        
        row_data = {
            'Cause_List': row['Cause_Tags'],
            'S_Bin': s_bin,
            'T_Bin': t_bin,
            'Fav_Home': fav_home,
            'Fav_Covered': fav_covered,
            'Total_Over': (total_score > game['total']),
            'Total_Under': (total_score < game['total']),
            'Is_Push': (total_score == game['total'])
        }
        valid_rows.append(row_data)
        
    df_miner = pd.DataFrame(valid_rows)
    
    # MINING
    print(f"Mining {len(df_miner)} games...")
    findings = []
    
    # 1. Define Cause Combos (Single + Pairs)
    # Get all unique causes
    all_causes = set()
    for c_list in df_miner['Cause_List']:
        all_causes.update(c_list)
    all_causes = sorted(list(all_causes))
    
    combo_list = []
    # Singles
    for c in all_causes: combo_list.append([c])
    # Pairs
    for pair in itertools.combinations(all_causes, 2):
        combo_list.append(list(pair))
        
    # 2. Iterate Combos + Market Buckets
    # Market Dimensions: S_Bin, T_Bin
    # We can iterate unique values in DF to save time
    s_bins = df_miner['S_Bin'].unique()
    t_bins = df_miner['T_Bin'].unique()
    
    for combo in combo_list:
        # Filter DF for this Combo (Row must have ALL causes in combo)
        # Vectorized check?
        # df_miner['Cause_List'] is list.
        # Boolean mask
        mask = df_miner['Cause_List'].apply(lambda x: all(c in x for c in combo))
        subset_combo = df_miner[mask]
        
        if len(subset_combo) < 200: continue
        
        # Inner Loop: Market Bins
        # 1. Broad (No Market Filter)
        evaluate_situation(subset_combo, combo, "ANY", findings)
        
        # 2. By Spread Bin
        for sb in s_bins:
            sub_s = subset_combo[subset_combo['S_Bin'] == sb]
            evaluate_situation(sub_s, combo, f"Spread={sb}", findings)
            
        # 3. By Total Bin
        for tb in t_bins:
            sub_t = subset_combo[subset_combo['T_Bin'] == tb]
            evaluate_situation(sub_t, combo, f"Total={tb}", findings)
            
        # 4. Combo Market (S+T)? (Optional, N likely too small)
        
    # Sort and Report
    findings_df = pd.DataFrame(findings)
    if findings_df.empty:
        print("No Situations Found.")
        return

    # Filter: ROI > 5%, N > 200
    good_sits = findings_df[
        (findings_df['N'] >= 200) & 
        (findings_df['ROI'] >= 5.0)
    ].sort_values('ROI', ascending=False)
    
    # Save Report
    with open(OUTPUT_REPORT, 'w') as f:
        f.write("# 💎 G9 Situation Mining Results (Track 4)\n")
        f.write(f"Analyzed {len(df_miner)} games. Found {len(good_sits)} Profitable Situations.\n\n")
        f.write(good_sits.to_markdown(index=False))
        
    print(f"Report Generated: {len(good_sits)} situations found.")

def evaluate_situation(df, causes, market_desc, results_list):
    n = len(df)
    if n < 200: return
    
    # Betting Types: Fav, Dog, Over, Under
    # Simple ROI: Win 0.9, Loss -1.0. Push 0.
    
    # Fav
    wins_fav = df['Fav_Covered'].sum()
    pnl_fav = (wins_fav * 0.9) - ((n - wins_fav) * 1.0) # Approx (ignoring pushes for speed)
    roi_fav = pnl_fav / n * 100
    
    # Dog
    # Dog wins if Fav Not Covered (ignoring push)
    wins_dog = n - wins_fav
    pnl_dog = (wins_dog * 0.9) - (wins_fav * 1.0)
    roi_dog = pnl_dog / n * 100
    
    # Over
    wins_over = df['Total_Over'].sum()
    pnl_over = (wins_over * 0.9) - ((n - wins_over) * 1.0)
    roi_over = pnl_over / n * 100
    
    # Under
    wins_under = df['Total_Under'].sum()
    pnl_under = (wins_under * 0.9) - ((n - wins_under) * 1.0)
    roi_under = pnl_under / n * 100
    
    # Add to list if good
    cause_str = "+".join(causes)
    
    if roi_fav >= 5.0:
        results_list.append({'Causes': cause_str, 'Market': market_desc, 'Bet': 'FAV_COVER', 'N': n, 'Win%': f"{wins_fav/n:.1%}", 'ROI': round(roi_fav, 2)})
    if roi_dog >= 5.0:
        results_list.append({'Causes': cause_str, 'Market': market_desc, 'Bet': 'DOG_COVER', 'N': n, 'Win%': f"{wins_dog/n:.1%}", 'ROI': round(roi_dog, 2)})
    if roi_over >= 5.0:
        results_list.append({'Causes': cause_str, 'Market': market_desc, 'Bet': 'OVER', 'N': n, 'Win%': f"{wins_over/n:.1%}", 'ROI': round(roi_over, 2)})
    if roi_under >= 5.0:
        results_list.append({'Causes': cause_str, 'Market': market_desc, 'Bet': 'UNDER', 'N': n, 'Win%': f"{wins_under/n:.1%}", 'ROI': round(roi_under, 2)})

if __name__ == "__main__":
    run_mining()
