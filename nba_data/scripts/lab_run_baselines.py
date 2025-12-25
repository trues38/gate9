import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.preprocessing import StandardScaler

# CONFIG
TRAIN_PATH = "processed/lab_train.csv"
TEST_PATH = "processed/lab_test.csv" # 23-24 Season Test Set (OOS)
REPORT_PATH = "g9_core_export/REPORTS/experiment_baseline_results.md"

# FEATURES
FEATS_QUANT = [
    'NetRtg_Sea', 'NetRtg_L10', 'Pace_L4', 'Pace_L16', 'Vol_Opp', 'Rest', 'GP'
]
FEATS_ODDS = [
    'Odds_Spread', 'Odds_Total', 'Moneyline'
]
TARGET = 'Regime_Label'
ODDS_PATH = "g9_core_export/DATA/nba_2008-2025.csv"

def get_action_v2(regime, spread, total, fav_team, is_home):
    """
    Action Logic v2: Strict Lab Conditions
    """
    action = "PASS"
    
    # 1. UNDER: Grind Regime AND Total [210, 240]
    if "Grind" in regime:
        if 210 <= total <= 240:
             action = "UNDER"
             
    # 2. DOG_SPREAD: Underdog/FavHold AND Spread [4.5, 12.5]
    # Note: 'Spread' here is usually positive (Absolute spread)
    elif ("Underdog" in regime) or ("Favorite_Hold" in regime):
        if 4.5 <= spread <= 12.5:
             # Logic check: We want to bet on DOG.
             # If regime says "Underdog_Resilience" -> Bet Dog.
             # If regime says "Favorite_Hold" -> Bet Fav??
             # User spec: "Favorite_Hold -> DOG +Spread" ??
             # Wait. User said: "Favorite_Hold → DOG +Spread only if Spread line in [4.5,12.5]"
             # This implies Fading the Favorite Hold? 
             # Or did user mean "Favorite_Collapse"?
             # Let's check the user prompt text:
             # "Favorite_Hold → DOG +Spread are maintained"
             # Actually earlier logic was: "Favorite_Hold -> FAV SPREAD".
             # User prompt says:
             # "Favorite_Hold → DOG +Spread ... only if line 4.5~12.5".
             # This contradicts "Favorite Hold" meaning (Favorite Holds lead = Cover).
             # Maybe user considers it a "Trap" in that range?
             # I will follow USER INSTRUCTION STRICTLY.
             action = "DOG_SPREAD"
             
    return action

def calculate_roi(df_pred, odds_df):
    """
    Calculates ROI for a dataframe of predictions [Date, Team, Pred_Regime]
    """
    # Need to join with Odds to get Result/Spread/Total
    # Optimized Join
    df_pred['Date'] = pd.to_datetime(df_pred['Date'])
    
    # Pre-build lookup for Odds
    odds_lookup = {}
    for idx, row in odds_df.iterrows():
        # Home Key
        odds_lookup[(row['date'], row['home'])] = row
        # Away Key
        odds_lookup[(row['date'], row['away'])] = row
        
    pnl_list = []
    action_list = []
    
    mapping_rev = {
        'atl': 'ATLANTA HAWKS', 'bos': 'BOSTON CELTICS', 'bkn': 'BROOKLYN NETS', 'cha': 'CHARLOTTE HORNETS', 'chi': 'CHICAGO BULLS', 'cle': 'CLEVELAND CAVALIERS', 'dal': 'DALLAS MAVERICKS', 'den': 'DENVER NUGGETS', 'det': 'DETROIT PISTONS', 'gsw': 'GOLDEN STATE WARRIORS', 'hou': 'HOUSTON ROCKETS', 'ind': 'INDIANA PACERS', 'lac': 'LA CLIPPERS', 'lal': 'LOS ANGELES LAKERS', 'mem': 'MEMPHIS GRIZZLIES', 'mia': 'MIAMI HEAT', 'mil': 'MILWAUKEE BUCKS', 'min': 'MINNESOTA TIMBERWOLVES', 'nop': 'NEW ORLEANS PELICANS', 'nyk': 'NEW YORK KNICKS', 'okc': 'OKLAHOMA CITY THUNDER', 'orl': 'ORLANDO MAGIC', 'phi': 'PHILADELPHIA 76ERS', 'phx': 'PHOENIX SUNS', 'por': 'PORTLAND TRAIL BLAZERS', 'sac': 'SACRAMENTO KINGS', 'sas': 'SAN ANTONIO SPURS', 'tor': 'TORONTO RAPTORS', 'uta': 'UTAH JAZZ', 'was': 'WASHINGTON WIZARDS'
    }
    team_to_code = {v: k for k, v in mapping_rev.items()}
    
    for idx, row in df_pred.iterrows():
        team_name = row['Team']
        date = row['Date']
        code = team_to_code.get(team_name.lower())
        if not code:
            code = team_to_code.get(team_name) # Try original case
            
        if not code:
             pnl_list.append(0); action_list.append("SKIP_TEAM"); continue
             
        game = odds_lookup.get((date, code))
        if game is None:
             game = odds_lookup.get((date + pd.Timedelta(days=1), code)) # Fuzzy
             
        if game is None:
            pnl_list.append(0); action_list.append("SKIP_GAME"); continue
            
        # Parse Game
        is_home = (game['home'] == code)
        spread = game['spread']
        total = game['total']
        score_home = game['score_home']
        score_away = game['score_away']
        fav_team = game['whos_favored']
        
        # DECIDE
        action = get_action_v2(row['Regime_Label'], spread, total, fav_team, is_home)
        action_list.append(action)
        
        if action == "PASS":
            pnl_list.append(0)
            continue
            
        # GRADE
        pnl = 0.0
        home_margin = score_home - score_away
        total_score = score_home + score_away
        
        if action == "UNDER":
            if total_score < total: pnl = 0.9
            elif total_score > total: pnl = -1.0
            
        elif action == "DOG_SPREAD":
            # Bet is: Underdog covers (or Favorite fails to cover)
            # Logic: If we are Home Dog: Cover if HomeMargin > -Spread
            # If we are Away Dog: Cover if AwayMargin > -Spread (-HomeMargin > -Spread)
            # BUT WAIT. Logic v2 said "DOG_SPREAD" for BOTH Underdog and Fav_Hold regimes.
            # This implies we are betting ON THE TEAM IN QUESTION (row['Team']) to cover +Spread?
            # If team is Favorite (Fav_Hold), we can't bet +Spread usually (only -Spread).
            # If user said "Favorite_Hold -> DOG +Spread", it means BET AGAINST THEM (Fade).
            # I will assume "DOG_SPREAD" means "Bet on the Underdog of the match".
            # So if 'Team' is Fav, we bet Opponent. If 'Team' is Dog, we bet Team.
            
            # Identify who is Dog
            dog_is_home = (fav_team == 'away')
            
            # Did Dog Cover?
            dog_covered = False
            if dog_is_home:
                if home_margin > -spread: dog_covered = True
            else:
                if (score_away - score_home) > -spread: dog_covered = True
                
            if dog_covered: pnl = 0.9
            else: pnl = -1.0
            
        pnl_list.append(pnl)
        
    return pnl_list, action_list

def run_baselines():
    print("Loading Data...")
    train = pd.read_csv(TRAIN_PATH).dropna()
    # Ensure Test path is correct (previously valid set, now strictly use what exists)
    # Using 'processed/lab_test.csv' if available, else 'lab_valid.csv'
    # Check if 'lab_test.csv' has rows
    try:
        test = pd.read_csv(TEST_PATH).dropna()
        if len(test) == 0: raise ValueError
    except:
        print("Falling back to Validation Set (22-23)")
        test = pd.read_csv("processed/lab_valid.csv").dropna()
        
    print(f"Train: {len(train)}, Test: {len(test)}")
    odds_df = pd.read_csv(ODDS_PATH)
    odds_df['date'] = pd.to_datetime(odds_df['date'])

    # --- BASELINE A: QUANT ---
    print("Running Baseline A (Quant)...")
    clf_quant = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    clf_quant.fit(train[FEATS_QUANT], train[TARGET])
    test['Regime_A'] = clf_quant.predict(test[FEATS_QUANT])
    
    # ROI A
    df_a = test[['Date', 'Team']].copy()
    df_a['Regime_Label'] = test['Regime_A']
    pnl_a, actions_a = calculate_roi(df_a, odds_df)
    
    bets_a = [x for x in actions_a if x != "PASS"]
    roi_a = (sum(pnl_a) / len(bets_a) * 100) if bets_a else 0.0
    
    # --- BASELINE B: ODDS ---
    print("Running Baseline B (Odds)...")
    scaler = StandardScaler()
    X_train_odds = scaler.fit_transform(train[FEATS_ODDS])
    X_test_odds = scaler.transform(test[FEATS_ODDS])
    
    clf_odds = LogisticRegression(max_iter=1000)
    clf_odds.fit(X_train_odds, train[TARGET])
    test['Regime_B'] = clf_odds.predict(X_test_odds)
    
    # ROI B
    df_b = test[['Date', 'Team']].copy()
    df_b['Regime_Label'] = test['Regime_B']
    pnl_b, actions_b = calculate_roi(df_b, odds_df)
    
    bets_b = [x for x in actions_b if x != "PASS"]
    roi_b = (sum(pnl_b) / len(bets_b) * 100) if bets_b else 0.0

    # REPORT
    print(f"Quant F1: {f1_score(test[TARGET], test['Regime_A'], average='weighted'):.3f}")
    print(f"Quant ROI: {roi_a:.2f}% ({len(bets_a)} bets)")
    print(f"Odds F1: {f1_score(test[TARGET], test['Regime_B'], average='weighted'):.3f}")
    print(f"Odds ROI: {roi_b:.2f}% ({len(bets_b)} bets)")
    
    report = f"""
# 🧪 G9 Lab Baseline Results (Audit Phase)

## 💰 ROI Performance (Action Logic v2)
| Model | Input | F1 Score | Bets | ROI |
|---|---|---|---|---|
| **Baseline A** | Quant Metrics | **{f1_score(test[TARGET], test['Regime_A'], average='weighted'):.3f}** | {len(bets_a)} | **{roi_a:.2f}%** |
| **Baseline B** | Market Odds | **{f1_score(test[TARGET], test['Regime_B'], average='weighted'):.3f}** | {len(bets_b)} | **{roi_b:.2f}%** |

## 🎯 Audit Target
The LLM must beat **Odds ROI ({roi_b:.2f}%)** to prove alpha.
    """
    
    with open(REPORT_PATH, 'w') as f:
        f.write(report)

if __name__ == "__main__":
    run_baselines()
