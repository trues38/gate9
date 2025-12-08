import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("/Users/js/g9/.env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

MODEL = "deepseek/deepseek-v3.2-exp" # DeepSeek V3.2 Exp (Cheapest)

def generate_synthetic_story(game_data):
    """
    Takes raw boxscore data and generates a "Fake" AP Recap using LLM.
    """
    # 1. Extract Key Stats
    header = game_data.get('header', {})
    competitions = header.get('competitions', [{}])[0]
    competitors = competitions.get('competitors', [])
    
    if not competitors: return None
    
    home = competitors[0]
    away = competitors[1]
    
    matchup = f"{away['team']['displayName']} @ {home['team']['displayName']}"
    score = f"{away['score']} - {home['score']}"
    winner = home if int(home['score']) > int(away['score']) else away
    
    # Extract Leaders if available
    leaders_text = ""
    top_scorer_info = ""
    
    # Try to find boxscore players
    try:
        # Check both home and away team stats
        all_players = []
        for team in game_data.get('boxscore', {}).get('players', []):
            for player in team.get('statistics', []):
                # This structure varies, need robust parsing
                # Actually, looking at the raw file structure from grep, it seems boxscore->teams->statistics is team level.
                # Player level is usually boxscore->teams->athletes or similar, OR we use the 'leaders' section more aggressively.
                pass
                
        # Fallback: Parse 'leaders' section which we know exists
        if 'leaders' in competitions:
            for l in competitions['leaders']:
                display = l.get('displayValue', '')
                leader_wrapper = l.get('leaders', [{}])[0]
                athlete = leader_wrapper.get('athlete', {}).get('displayName', 'Unknown')
                stat_val = leader_wrapper.get('displayValue', '0')
                leaders_text += f"- {display}: {athlete} ({stat_val})\n"
                
                # Check for massive scoring nights (e.g. > 50)
                if 'points' in display.lower() or 'scoring' in display.lower():
                     try:
                         val = float(stat_val)
                         if val >= 40:
                             top_scorer_info = f"HISTORIC PERFORMANCE ALERT: {athlete} scored {stat_val} points!"
                     except:
                         pass
    except Exception as e:
        print(f"Stats check error: {e}")

    # 3. Build Prompt
    prompt = f"""
You are a Sports Historian and Journalist.
Reconstruct the game narrative based ONLY on these stats.
Write a passionate, AP-style game recap (approx 300 words).

*** CRITICAL INSTRUCTION ***
If a player has an exceptionally high stat (e.g. >40 points), YOU MUST FOCUS THE ENTIRE STORY ON THEM.
This is likely a historic performance.

GAME: {matchup}
SCORE: {score}
DATE: {header.get('season', {}).get('year', 'Unknown Date')}

KEY STATS & LEADERS:
{leaders_text}
{top_scorer_info}

WINNER: {winner['team']['displayName']}

Write the story now.
"""

    # 3. Call LLM
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating story: {e}")
        return None

def process_legacy_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    print(f"🧠 Synthesizing Narrative for {filepath}...")
    story = generate_synthetic_story(data)
    
    if story:
        print("\n" + "="*50)
        print("📜 SYNTHETIC HISTORICAL RECORD")
        print("="*50)
        print(story[:500] + "...\n")
        
        # Save as if it were a real crawled story
        dummy_id = os.path.basename(filepath).replace('legacy_', '').replace('.json', '')
        output_path = f"nba_data/stories_raw/story_{dummy_id}.json"
        
        output_data = {
            "game_id": dummy_id,
            "title": "Synthetic Recap",
            "body": story, # This feeds the Regime Engine!
            "source": "AI_Reconstruction"
        }
        
        with open(output_path, 'w') as f_out:
            json.dump(output_data, f_out)
        print(f"✅ Saved to {output_path}")

if __name__ == "__main__":
    import glob
    from tqdm import tqdm
    
    print("🚀 Starting Legacy Narrative Synthesis (DeepSeek V3.2 Exp)...")
    
    import random
    
    # Get all legacy files
    input_files = glob.glob("nba_data/legacy_raw/*.json")
    random.shuffle(input_files) # Shuffle for parallel execution
    print(f"Found {len(input_files)} legacy games.")
    
    for filepath in tqdm(input_files):
        # Check if output already exists
        dummy_id = os.path.basename(filepath).replace('legacy_', '').replace('.json', '')
        output_path = f"nba_data/stories_raw/story_{dummy_id}.json"
        
        if os.path.exists(output_path):
            continue
            
        process_legacy_file(filepath)
