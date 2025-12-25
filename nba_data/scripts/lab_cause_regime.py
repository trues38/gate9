import pandas as pd
import duckdb
import numpy as np
from datetime import timedelta

# CONFIG
DB_PATH = "nba_sql.duckdb"
ODDS_PATH = "g9_core_export/DATA/nba_2008-2025.csv"
OUTPUT_REPORT = "g9_core_export/REPORTS/lab_cause_regime_results.md"
REGIME_PATH = "g9_core_export/DATA/nba_regime_index.json"

def load_data():
    print("Loading Data...")
    con = duckdb.connect(DB_PATH, read_only=True)
    
    # Needs Opponent Cols for Schedule/Tempo comparisons
    # rdata_treasury has 'days_since_last' (Rest). Does it have Opp Rest? 
    # Schema showed 'days_since_last_o' (Opp Rest).
    # Schema showed 'avg_P_4' and 'avg_P_opp_4'.
    # Schema showed 'NetRtg_Sea', 'NetRtg_L10'.
    # Volatility? 'Vol_Sea' exists.
    
    query = """
        SELECT 
            Date, Team, Opponent,
            days_since_last as Rest,
            days_since_last_o as Rest_Opp,
            avg_P_4 as Pace_L4,
            avg_P_opp_4 as Pace_L4_Opp,
            NetRtg_Sea, NetRtg_L10,
            Vol_Sea,
            games_played as GP
        FROM rdata_treasury
        WHERE games_played > 10
    """
    df = con.execute(query).fetchdf()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Team'] = df['Team'].str.upper().str.strip()
    
    # Load Odds for Result/Edge
    odds = pd.read_csv(ODDS_PATH)
    odds['date'] = pd.to_datetime(odds['date'])
    
    # Load Regimes (Labels)
    import json
    with open(REGIME_PATH, 'r') as f:
        rdata = json.load(f)
    regimes = pd.DataFrame(rdata)
    regimes['date'] = pd.to_datetime(regimes['date'])
    regimes['team'] = regimes['team'].str.upper().str.strip()
    regimes = regimes.rename(columns={'regime_type': 'Outcome_Regime'})
    
    return df, odds, regimes

def tag_causes(df, odds_lookup, team_to_code):
    print("Tagging Causes...")
    
    causes = []
    
    # Pre-calc League Stats
    league_avg_netrtg = df.groupby('Date')['NetRtg_L10'].transform('mean')
    
    for idx, row in df.iterrows():
        matches = []
        
        # 1. SCHEDULE
        # Crunch: Rest Diff <= -1 AND Rest=0 (B2B)
        if pd.notnull(row['Rest']) and pd.notnull(row['Rest_Opp']):
            rest_diff = row['Rest'] - row['Rest_Opp']
            if rest_diff <= -1 and row['Rest'] == 0:
                matches.append("CAUSE_SCHED_CRUNCH")
            if rest_diff >= 2:
                matches.append("CAUSE_SCHED_ADV")
            
        # 2. STABILITY (Vol Proxy)
        # Assuming Vol_Sea ~ 0.1 median.
        if pd.notnull(row['Vol_Sea']):
            if row['Vol_Sea'] > 0.15: 
                matches.append("CAUSE_VOL_CHAOS")
            if row['Vol_Sea'] < 0.07: 
                matches.append("CAUSE_VOL_STABLE")
            
        # 3. MOMENTUM (Divergence)
        if pd.notnull(row['NetRtg_L10']) and pd.notnull(row['NetRtg_Sea']):
            if abs(row['NetRtg_L10'] - row['NetRtg_Sea']) >= 6.0:
                matches.append("CAUSE_NETRTG_DIVERGENCE")
            
        # 4. MARKET GAP (Simplified Proxy)
        # Using NetRtg vs Spread? Skipping detailed Edge for now to avoid complexity.
             
        # 5. TEMPO (Pace Mismatch)
        if pd.notnull(row['Pace_L4']) and pd.notnull(row['Pace_L4_Opp']):
            if abs(row['Pace_L4'] - row['Pace_L4_Opp']) >= 5.0:
                matches.append("CAUSE_PACE_MISMATCH")
            
        causes.append(matches)
        
    df['Cause_Tags'] = causes
    return df

def get_odds_game(row, lookup):
    return lookup.get((row['Date'], row['Team'])) 

def run_experiments():
    df, odds, regimes = load_data()
    
    # Prepare Lookup
    mapping_rev = {
        'atl': 'ATLANTA HAWKS', 'bos': 'BOSTON CELTICS', 'bkn': 'BROOKLYN NETS', 'cha': 'CHARLOTTE HORNETS', 'chi': 'CHICAGO BULLS', 'cle': 'CLEVELAND CAVALIERS', 'dal': 'DALLAS MAVERICKS', 'den': 'DENVER NUGGETS', 'det': 'DETROIT PISTONS', 'gsw': 'GOLDEN STATE WARRIORS', 'hou': 'HOUSTON ROCKETS', 'ind': 'INDIANA PACERS', 'lac': 'LA CLIPPERS', 'lal': 'LOS ANGELES LAKERS', 'mem': 'MEMPHIS GRIZZLIES', 'mia': 'MIAMI HEAT', 'mil': 'MILWAUKEE BUCKS', 'min': 'MINNESOTA TIMBERWOLVES', 'nop': 'NEW ORLEANS PELICANS', 'nyk': 'NEW YORK KNICKS', 'okc': 'OKLAHOMA CITY THUNDER', 'orl': 'ORLANDO MAGIC', 'phi': 'PHILADELPHIA 76ERS', 'phx': 'PHOENIX SUNS', 'por': 'PORTLAND TRAIL BLAZERS', 'sac': 'SACRAMENTO KINGS', 'sas': 'SAN ANTONIO SPURS', 'tor': 'TORONTO RAPTORS', 'uta': 'UTAH JAZZ', 'was': 'WASHINGTON WIZARDS'
    }
    team_to_code = {v: k for k, v in mapping_rev.items()}
    
    odds_lookup = {}
    for idx, row in odds.iterrows():
        # Map Code back to Full Name for Key? No, use (Date, Name) as key
        home_name = mapping_rev.get(row['home'], 'UNKNOWN')
        away_name = mapping_rev.get(row['away'], 'UNKNOWN')
        odds_lookup[(row['date'], home_name)] = row
        odds_lookup[(row['date'], away_name)] = row
    
    # Tag
    df = tag_causes(df, odds_lookup, team_to_code)
    
    # Merge Regimes
    df = pd.merge(df, regimes, left_on=['Date', 'Team'], right_on=['date', 'team'], how='inner')
    
    # Explode Causes
    df_exp = df.explode('Cause_Tags')
    df_exp = df_exp.dropna(subset=['Cause_Tags']) # Remove rows with no cause
    
    # --- EXP A: Distribution ---
    print("Running Exp A (Distribution)...")
    dist = df_exp.groupby(['Cause_Tags', 'Outcome_Regime']).size().reset_index(name='Count')
    total = df_exp.groupby('Cause_Tags').size().reset_index(name='Total')
    dist = pd.merge(dist, total, on='Cause_Tags')
    dist['Ratio'] = dist['Count'] / dist['Total']
    
    # Filter Significant
    sig_dist = dist[dist['Ratio'] >= 0.3].sort_values(['Cause_Tags', 'Ratio'], ascending=[True, False])
    
    # --- EXP B: Betting Hit Rate ---
    print("Running Exp B (Betting)...")
    bet_res = []
    
    # --- EXP B: Betting Hit Rate ---
    print("Running Exp B (Betting)...")
    bet_res = []
    
    # Helper for betting calc
    def calc_betting_stats(group_df, label):
        wins_fav = 0
        wins_dog = 0
        wins_over = 0
        wins_under = 0
        valid_spread = 0
        valid_total = 0
        
        for idx, row in group_df.iterrows():
            game = odds_lookup.get((row['Date'], row['Team']))
            if game is None: continue
            
            # spread result
            is_home_team = (game['home'] == team_to_code.get(row['Team'].lower()))
            fav_team = game['whos_favored']
            spread = game['spread']
            score_diff = game['score_home'] - game['score_away']
            total_score = game['score_home'] + game['score_away']
            
            # Did Favorite Cover?
            fav_covered = False
            margin = score_diff # Home - Away
            
            # If Home Fav: Cover if Margin > Spread
            # If Away Fav: Cover if Margin < -Spread
            if fav_team == 'home':
                if margin > spread: fav_covered = True
            elif fav_team == 'away':
                if margin < -spread: fav_covered = True
            # Else Pickem? Assume no cover.
                
            if fav_covered: wins_fav += 1
            else: wins_dog += 1
            valid_spread += 1
            
            # Total
            if total_score > game['total']: wins_over += 1
            elif total_score < game['total']: wins_under += 1
            valid_total += 1
            
        rate_fav = wins_fav / valid_spread if valid_spread else 0
        rate_dog = wins_dog / valid_spread if valid_spread else 0
        rate_over = wins_over / valid_total if valid_total else 0
        rate_under = wins_under / valid_total if valid_total else 0
        
        return {
            "Cause": label,
            "N": valid_spread,
            "Fav_Cover%": rate_fav,
            "Dog_Cover%": rate_dog,
            "Over%": rate_over,
            "Under%": rate_under
        }

    # Group by Cause
    for cause, group in df_exp.groupby('Cause_Tags'):
        if len(group) < 50: continue
        bet_res.append(calc_betting_stats(group, cause))
        
    bet_df = pd.DataFrame(bet_res)
    
    # --- EXP D: Dead Zone Rescue ---
    # Dead Zone: Standard lines where odds usually efficient. 
    # Defined as: Spread < 7.5 AND Total in [215, 235] (Average zone)
    print("Running Exp D (Dead Zone)...")
    dead_res = []
    
    # Filter for Dead Zone
    dead_zone_rows = []
    for idx, row in df_exp.iterrows():
        game = odds_lookup.get((row['Date'], row['Team']))
        if game is not None:
            if game['spread'] < 7.5 and 215 <= game['total'] <= 235:
                dead_zone_rows.append(row)
                
    df_dead = pd.DataFrame(dead_zone_rows)
    if not df_dead.empty:
        for cause, group in df_dead.groupby('Cause_Tags'):
            if len(group) < 50: continue
            dead_res.append(calc_betting_stats(group, f"{cause} (DeadZone)"))
            
    dead_df = pd.DataFrame(dead_res)
    
    # WRITE REPORT
    with open(OUTPUT_REPORT, 'w') as f:
        f.write("# 🔬 G9 Cause Regime Lab Results\n\n")
        
        f.write("## Exp A: Cause -> Outcome Distribution (Significant > 30%)\n")
        f.write(sig_dist.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## Exp B: Betting Performance (Filter: N>200)\n")
        if not bet_df.empty:
            f.write(bet_df[bet_df['N'] > 100].sort_values('N', ascending=False).to_markdown(index=False))
        else:
            f.write("No significant results.")
        f.write("\n\n")
        
        f.write("## Exp D: Dead Zone Performance (Spread < 7.5, Total 215-235)\n")
        if not dead_df.empty:
            f.write(dead_df.sort_values('N', ascending=False).to_markdown(index=False))
        else:
            f.write("No Dead Zone results.")
        f.write("\n\n")
        
    print("Report Generated.")

if __name__ == "__main__":
    run_experiments()
