
import json
import os
import time
import requests
from tqdm import tqdm
from datetime import datetime

# Config
QUANT_INDEX = "processed/master_chronicle_index.json"
REALITY_INDEX = "data/headlines_2019_2025.jsonl"
OUTPUT_FILE = "processed/master_regime_index.json"
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")

# Hardcoded Fallback (from run_oracle_chronicles.py)
if not API_KEY:
    os.environ["OPENROUTER_API_KEY"] = "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"
    API_KEY = os.environ["OPENROUTER_API_KEY"]

MODEL_NAME = "deepseek/deepseek-chat" # or deepseek-v3 if available

# Name Mapping (ESPN -> Quant)
TEAM_MAP = {
    "LA Clippers": "Los Angeles Clippers"
}

def normalize_name(name):
    return TEAM_MAP.get(name, name)

def load_data():
    print("📥 Loading Data...")
    
    # 1. Load Reality (Headlines)
    # Map: (date_str, team_name) -> headline_info
    reality_map = {}
    with open(REALITY_INDEX, 'r') as f:
        for line in f:
            try:
                row = json.loads(line)
                date = row['date'].replace("-", "") # 2019-10-22 -> 20191022 to match quant? 
                # Wait, Quant usually uses YYYY-MM-DD in 'date' field? 
                # Check snippet: "date": "2014-10-28"
                # So we keep dashes.
                date = row['date']
                
                home = normalize_name(row['home_team'])
                away = normalize_name(row['away_team'])
                
                # Store for both teams
                info = {
                    "headline": row.get('headline'),
                    "desc": row.get('description')
                }
                
                reality_map[(date, home)] = info
                reality_map[(date, away)] = info
                
            except: pass
            
    print(f"✅ Loaded Reality Map: {len(reality_map)} team-games")
    
    # 2. Load Quant
    with open(QUANT_INDEX, 'r') as f:
        quant_data = json.load(f)
        
    print(f"✅ Loaded Quant Data: {len(quant_data)} games")
    
    return quant_data, reality_map

def classify_regime(game, headline_info):
    """
    Calls LLM to classify the regime based on Expectation vs Reality.
    """
    if not API_KEY:
        return {"error": "No API Key"}
        
    # Construct Prompt
    edge = game.get('edge_score', 0)
    fav_pct = game.get('fav_pct', 0.5) * 100
    flow = game.get('flow_state', 'Unknown')
    team = game.get('team')
    matchup = game.get('matchup')
    result = game.get('result') # Win/Loss
    headline = headline_info['headline']
    desc = headline_info['desc']
    
    prompt = f"""
    Analyze the "Regime" of this NBA game by comparing Pre-Game Expectation vs Post-Game Reality.
    
    [EXPECTATION]
    - Matchup: {matchup}
    - Focus Team: {team}
    - Edge Score: {edge:.1f} (If > 60: Strong Fav, If < 40: Underdog, 40-60: Neutral)
    - Win Probability: {fav_pct:.1f}%
    - Flow State: {flow}
    
    [REALITY]
    - Result: {result}
    - Headline: "{headline}"
    - Detail: "{desc}"
    
    [TASK]
    Classify what kind of "Regime" this game represents.
    Return a JSON object with:
    1. "regime_type": Choose ONE from [Favorite_Hold, Favorite_Collapse, Underdog_Upset, Underdog_Resilience, Grind_Win, Grind_Loss, Blowout_Win, Blowout_Loss, Star_Takeover].
    2. "narrative_delta": One sentence explaining how reality differed from (or matched) expectation.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3, # Low temp for classification
                    "response_format": {"type": "json_object"}
                },
                timeout=15
            )
            
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            elif resp.status_code == 429:
                print(f"⚠️ Rate Limit (429). Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
            else:
                print(f"⚠️ API Error {resp.status_code}: {resp.text}")
                return None
                
        except Exception as e:
            print(f"LLM Error: {e}")
            time.sleep(1)
    
    return None

import concurrent.futures
import threading

LOCK = threading.Lock()

def process_single_regime(g, h_info):
    llm_out = classify_regime(g, h_info)
    if llm_out:
        # Clean Markdown
        cleaned = llm_out.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            parsed = json.loads(cleaned)
            merged = {
                **g,
                **parsed,
                "headline": h_info['headline']
            }
            return merged
        except Exception as e:
            # print(f"JSON Parse Error: {e}")
            return None
    return None

def run_builder():
    quant, reality = load_data()
    
    # Filter for 2019+ and Reality Exists
    target_games = []
    
    # Output file (JSONL)
    OUTPUT_JSONL = "processed/master_regime_index.jsonl"
    
    # Resume Logic
    processed_ids = set()
    if os.path.exists(OUTPUT_JSONL):
        print("resume: Scanning existing processed games...")
        with open(OUTPUT_JSONL, 'r') as f:
            for line in f:
                try:
                    row = json.loads(line)
                    processed_ids.add(row['game_id'])
                except: pass
    
    print(f"📦 Resuming... {len(processed_ids)} games already done.")

    for g in quant:
        dt = g.get('date') # YYYY-MM-DD
        if dt < "2019-10-22": continue
        
        # Skip if done
        if g.get('game_id') in processed_ids:
            continue
            
        tm = g.get('team')
        if (dt, tm) in reality:
            if reality[(dt, tm)]['headline']:
                target_games.append((g, reality[(dt, tm)]))
                
    print(f"🎯 Games Remaining to Process: {len(target_games)}")
    if not target_games:
        print("✅ All done!")
        return

    # Threaded Execution
    WORKERS = 8 # Be aggressive but polite
    
    print(f"🚀 Starting Production Classification (Workers: {WORKERS})...")
    
    with open(OUTPUT_JSONL, 'a') as f_out: 
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(process_single_regime, item[0], item[1]): item[0] for item in target_games}
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                result = future.result()
                if result:
                    with LOCK:
                        f_out.write(json.dumps(result) + "\n")
                        f_out.flush()
    
    print("✅ Regime Builder Complete.")

if __name__ == "__main__":
    run_builder()
