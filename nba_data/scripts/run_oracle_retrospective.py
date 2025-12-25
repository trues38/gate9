
import pandas as pd
import json
import os
import sys
sys.path.append(os.getcwd())
import requests
from tqdm import tqdm
from datetime import datetime

# Load .env manually
env_file = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip().strip('"').strip("'")

# Force Hardcoded Key if previous failed (Safety)
os.environ["OPENROUTER_API_KEY"] = "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"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat"

def get_retrospective_commentary(game_row, story_row):
    prompt = f"""
    CONTEXT:
    You are 'The Oracle of the Hardwood', an AI historian explaining NBA history through the lens of "The Regime" (Quantitative Momentum).
    
    THE GAME (Historical Event):
    - Date: {game_row['date']}
    - Matchup: {game_row['team']} vs {game_row['opp']}
    - Result: {story_row['story_headline']} (Winner: {story_row['winner']})
    
    THE QUANTITATIVE SIGNAL (The Hidden Truth):
    - Edge Score: {game_row['edge_score']} (If > 60, Favorite was Strong. If < 40, Underdog had flow.)
    - Flow State: {game_row['flow_state']}
    - Fatigue: {game_row['fatigue_state']}
    
    YOUR TASK:
    Explain WHY this result happened using the Quant Signal.
    Did the Edge Score predict the dominance? Or was it a "Structural Collapse" (High Edge, but Upset happened)?
    Connect the "Story" (Headline) to the "Numbers" (Edge/Flow).
    
    STYLE:
    - Insightful, Analytical but Mystic.
    - "The numbers whispered..."
    - Max 3 sentences.
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://antigravity.ai", 
            "X-Title": "Emergent Regime Engine"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0, 
            "max_tokens": 250
        }
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"


TEAM_MAP = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA',
    'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
    'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
}

def run():
    print("📜 ORACLE RETROSPECTIVE 2023-2024")
    
    # 1. Load Data
    df_quant = pd.read_csv("processed/backtest_results_exp1.csv")
    df_quant['date'] = pd.to_datetime(df_quant['date'])
    
    with open("quant_engine/upset_library_enriched.json", 'r') as f:
        lib_data = json.load(f)
    df_news = pd.DataFrame(lib_data)
    df_news['date'] = pd.to_datetime(df_news['date'])
    
    # 2. Filter for Post-2022
    df_quant = df_quant[df_quant['date'] >= '2023-01-01'].copy()
    
    merged_rows = []
    
    print("🔍 Matching Quant Data with Historical News...")
    for idx, q_row in tqdm(df_quant.iterrows(), total=len(df_quant)):
        # Convert Team to Abbr
        team_abbr = TEAM_MAP.get(q_row['team'])
        if not team_abbr: continue
        
        # Match if date matches and (team_abbr == favorite or team_abbr == underdog)
        matches = df_news[
            (df_news['date'] == q_row['date']) & 
            ((df_news['favorite'] == team_abbr) | (df_news['underdog'] == team_abbr))
        ]
        
        if not matches.empty:
            story = matches.iloc[0]
            game_id = f"{q_row['date']}_{sorted([q_row['team'], q_row['opp']])[0]}"
            merged_rows.append({
                "id": game_id,
                "quant": q_row,
                "story": story
            })
    
    # Deduplicate
    unique_games = {item['id']: item for item in merged_rows}.values()
    print(f"✅ Found {len(unique_games)} intersected games with both Quant and News.")
    
    # 4. Generate
    output_path = "reports/oracle_retrospective_23_24.md"
    with open(output_path, 'w') as f:
        f.write("# 📜 ORACLE RETROSPECTIVE: 2023-2024\n\n")
        
        for item in tqdm(list(unique_games)[:50]): # Limit to 50 for demo
            commentary = get_retrospective_commentary(item['quant'], item['story'])
            
            f.write(f"### {item['quant']['date'].strftime('%Y-%m-%d')} | {item['story']['story_headline']}\n")
            f.write(f"- **Regime**: Edge {item['quant']['edge_score']} ({item['quant']['flow_state']})\n")
            f.write(f"> **{commentary.strip()}**\n\n")
            f.write("---\n")
            f.flush()

    print(f"DONE. Saved to {output_path}")

if __name__ == "__main__":
    run()
