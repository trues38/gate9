import pandas as pd
import json
import os
import argparse
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.metrics import f1_score
from collections import Counter

# CONFIG
TEST_PATH = "processed/lab_test.jsonl"
ODDS_PATH = "g9_core_export/DATA/nba_2008-2025.csv"
OUTPUT_PATH = "g9_core_export/REPORTS/audit_llm_log.csv"
ENV_PATH = "/Users/js/g9/nba_data/g9_core_export/.env"

# API SETUP
load_dotenv(ENV_PATH)
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None

if not API_KEY:
    print("⚠️  WARNING: No API Key found. Results will be Mock.")
    CLIENT = None
else:
    CLIENT = OpenAI(api_key=API_KEY, base_url=BASE_URL)

MODEL_NAME = "openai/gpt-4o-mini"
SYSTEM_PROMPT = """You are G9 Structural Analyst.
Your goal is to predict the 'Structural Regime' of an upcoming NBA game based on pre-game metrics.
You must look for NON-LINEAR patterns between Team metrics and Market Odds.

INPUT:
- Market: Spread, Total (Pre-game closing lines)
- Team Metrics: Pace, NetRtg, Rest, Volatility (Pre-game)

OUTPUT:
- Return a JSON object strictly following the schema.
- Do NOT output markdown or explanation outside JSON.
- Regime Types: [Favorite_Hold, Star_Takeover, Blowout_Win, Blowout_Loss, Favorite_Collapse, Underdog_Resilience, Underdog_Upset, Grind_Win, Grind_Loss]
"""

# GLOBAL ODDS DF
ODDS_DF = None

def load_odds():
    global ODDS_DF
    ODDS_DF = pd.read_csv(ODDS_PATH)
    ODDS_DF['date'] = pd.to_datetime(ODDS_DF['date'])

def construct_prompt(record):
    f = record['features']
    prompt = f"""
GAME CONTEXT:
ID: {record['id']}
Date: {record['date']}
Team: {record['team']}

MARKET:
Spread: {f.get('spread')} (Favored: {f.get('favored_team')})
Total: {f.get('total')}

METRICS:
Net Rating (Season): {f.get('net_rtg_sea')}
Net Rating (L10): {f.get('net_rtg_L10')}
Pace (L4): {f.get('pace_L4')}
Rest Days: {f.get('rest')}

TASK:
Based on the deviation between Market Expectation (Spread/Total) and Team Metrics (NetRtg/Pace),
Classify the most likely Structural Regime for this team.

RESPONSE FORMAT:
{{
  "regime_type": "Enum Value",
  "confidence": 0.0-1.0,
  "top_features": ["list", "of", "reasons"],
  "reason": "Short explanation using features"
}}
"""
    return prompt

def call_llm_once(prompt, temp=0.1):
    if not CLIENT:
        return {"regime_type": "Grind_Win", "top_features": ["pace_L4"], "reason": "Mock"}
    try:
        response = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temp
        )
        return json.loads(response.choices[0].message.content)
    except:
        return None

def call_llm_consistency(prompt, n=5):
    """
    Calls LLM n times in parallel. Returns Consensus Regime and Confidence Score.
    """
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(call_llm_once, prompt, temp=0.1 + (i*0.05)) for i in range(n)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res: results.append(res)
            
    if not results: return "Unknown", 0.0, [], "Fail"
    
    # Vote
    votes = [r.get('regime_type', 'Unknown') for r in results]
    counts = Counter(votes)
    winner, win_count = counts.most_common(1)[0]
    confidence = win_count / len(results)
    
    # Get representative Features/Reason from a winning response
    rep_res = next((r for r in results if r.get('regime_type') == winner), results[0])
    
    return winner, confidence, rep_res.get('top_features', []), rep_res.get('reason', '')

def get_action_v2(regime, spread, total):
    """
    Action Logic v2: Strict Lab Conditions
    """
    action = "PASS"
    if spread is None or total is None: return "PASS"
    
    # 1. UNDER: Grind Regime AND Total [210, 240]
    if "Grind" in regime:
        if 210 <= total <= 240:
             action = "UNDER"
             
    # 2. DOG_SPREAD: Underdog/FavHold AND Spread [4.5, 12.5]
    elif ("Underdog" in regime) or ("Favorite_Hold" in regime):
        if 4.5 <= spread <= 12.5:
             action = "DOG_SPREAD"
             
    return action

def check_odds_copy(features):
    """
    Returns True if features rely heavily on odds keywords.
    """
    banned = ['odds', 'spread', 'total', 'market', 'line', 'favorite', 'underdog']
    for f in features:
        f_lower = str(f).lower()
        for b in banned:
            if b in f_lower: return True
    return False

def grade_bet(record, action, odds_df):
    if action == "PASS": return 0.0
    
    # Lookup Game
    date_ts = pd.to_datetime(record['date'])
    # Re-use simplified mapping logic or better fuzzy match
    # For Lab, we rely on mapping logic in run_baselines or here.
    # Simplified: Name match
    
    mapping_rev = {
        'atl': 'ATLANTA HAWKS', 'bos': 'BOSTON CELTICS', 'bkn': 'BROOKLYN NETS', 'cha': 'CHARLOTTE HORNETS', 'chi': 'CHICAGO BULLS', 'cle': 'CLEVELAND CAVALIERS', 'dal': 'DALLAS MAVERICKS', 'den': 'DENVER NUGGETS', 'det': 'DETROIT PISTONS', 'gsw': 'GOLDEN STATE WARRIORS', 'hou': 'HOUSTON ROCKETS', 'ind': 'INDIANA PACERS', 'lac': 'LA CLIPPERS', 'lal': 'LOS ANGELES LAKERS', 'mem': 'MEMPHIS GRIZZLIES', 'mia': 'MIAMI HEAT', 'mil': 'MILWAUKEE BUCKS', 'min': 'MINNESOTA TIMBERWOLVES', 'nop': 'NEW ORLEANS PELICANS', 'nyk': 'NEW YORK KNICKS', 'okc': 'OKLAHOMA CITY THUNDER', 'orl': 'ORLANDO MAGIC', 'phi': 'PHILADELPHIA 76ERS', 'phx': 'PHOENIX SUNS', 'por': 'PORTLAND TRAIL BLAZERS', 'sac': 'SACRAMENTO KINGS', 'sas': 'SAN ANTONIO SPURS', 'tor': 'TORONTO RAPTORS', 'uta': 'UTAH JAZZ', 'was': 'WASHINGTON WIZARDS'
    }
    team_to_code = {v: k for k, v in mapping_rev.items()}
    code = team_to_code.get(record['team'])
    
    if not code: return 0.0
    
    # Lookup
    day_games = odds_df[odds_df['date'] == date_ts]
    if day_games.empty: 
        day_games = odds_df[odds_df['date'] == date_ts + pd.Timedelta(days=1)]
        
    game = day_games[(day_games['home'] == code) | (day_games['away'] == code)]
    if game.empty: return 0.0
    game = game.iloc[0]
    
    score_home = game['score_home']
    score_away = game['score_away']
    spread = game['spread']
    total_line = game['total']
    fav_team = game['whos_favored']
    
    pnl = 0.0
    total_score = score_home + score_away
    
    if action == "UNDER":
        if total_score < total_line: pnl = 0.9
        elif total_score > total_line: pnl = -1.0
        
    elif action == "DOG_SPREAD":
        is_home = (game['home'] == code)
        dog_is_home = (fav_team == 'away')
        dog_covered = False
        
        # Assumption: We bet ON the Dog if we are Dog, or Against Fav if we are FavHold?
        # Standard: Action applies to the TEAM being analyzed. 
        # But if the action is "DOG_SPREAD" and the team is Favorite, it's contradictory.
        # However, logic v2 says: Favorite_Hold -> DOG_SPREAD.
        # This implies we take the DOG side (Opponent) in that game.
        # So "DOG_SPREAD" means "Bet the Underdog of this match".
        
        if dog_is_home:
             if (score_home - score_away) > -spread: dog_covered = True
        else:
             if (score_away - score_home) > -spread: dog_covered = True
             
        if dog_covered: pnl = 0.9
        else: pnl = -1.0
        
    return pnl

def run_audit(limit=50):
    print(f"🕵️ Starting Sniper Audit (N={limit}, Consistency=5x)...")
    load_odds()
    
    with open(TEST_PATH, 'r') as f:
        lines = f.readlines()
        
    print(f"Loaded {len(lines)} samples.")
    results = []
    
    processed = 0
    for line in lines:
        if processed >= limit: break
        
        record = json.loads(line)
        prompt = construct_prompt(record)
        
        # 1. Consensus Call
        print(f"[{processed+1}/{limit}] Auditing {record['team']}...")
        pred_regime, conf, feats, reason = call_llm_consistency(prompt)
        
        # 2. Action Logic v2
        fdata = record['features']
        action = "PASS"
        if conf >= 0.6: # 3/5 Votes Minimum
            action = get_action_v2(pred_regime, fdata.get('spread'), fdata.get('total'))
            
        # 3. Odds Copy Check
        is_copy = check_odds_copy(feats)
        
        # 4. Grading
        pnl = grade_bet(record, action, ODDS_DF)
        
        results.append({
            "id": record['id'],
            "pred_regime": pred_regime,
            "true_regime": record['label'],
            "confidence": conf,
            "action": action,
            "pnl": pnl,
            "odds_copy": is_copy,
            "reason": reason
        })
        processed += 1
        
    # REPORTING
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_PATH, index=False)
    
    # 1. Action Performance
    bets = df[df['action'] != "PASS"]
    roi_total = bets['pnl'].sum() / len(bets) * 100 if len(bets) > 0 else 0.0
    
    print("\n📊 AUDIT REPORT")
    print(f"Total ROI: {roi_total:.2f}% (Bets: {len(bets)}/{len(df)})")
    
    # 2. Breakdown by Action
    print("\n[Action Breakdown]")
    print(bets.groupby('action')['pnl'].agg(['count', 'mean', 'sum']))
    
    # 3. Odds Copy Impact
    print("\n[Odds Copy Impact]")
    print(bets.groupby('odds_copy')['pnl'].mean() * 100)
    
    # 4. Confidence Impact
    print("\n[Confidence Impact]")
    bets['conf_bin'] = pd.cut(bets['confidence'], bins=[0.5, 0.7, 0.9, 1.0])
    print(bets.groupby('conf_bin')['pnl'].mean() * 100)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    run_audit(limit=args.limit)
