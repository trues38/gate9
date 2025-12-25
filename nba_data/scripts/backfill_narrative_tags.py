
import json
import os
import sys
import time
import requests
from typing import List, Dict

# Set up environment
sys.path.append(os.getcwd())
env_file = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip().strip('"').strip("'")

# Force Hardcoded Key (Safety)
if not os.getenv("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = "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"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat"

def get_narrative_tags(story: Dict) -> Dict:
    """
    Uses LLM to tag a game based on its story.
    Returns JSON: { "primary_tag": "...", "secondary_tags": [...] }
    """
    headline = story.get('story_headline', '')
    body = story.get('story_body', '')[:1000] # Truncate for cost
    winner = story.get('winner', 'Unknown')
    favorite = story.get('favorite', 'Unknown')
    
    prompt = f"""
    Analyze this NBA game story and extract "Narrative Tags".
    
    GAME:
    - Headline: {headline}
    - Winner: {winner} (Favorite: {favorite})
    - Story: {body}
    
    TASK:
    Classify this game's narrative into standard NBA Archetypes.
    
    OUTPUT JSON FORMAT:
    {{
        "primary_tag": "One of [Star_Injury, Rest_Advantage, Back_to_Back, Revenge_Game, Shooting_Slump, Hot_Hand, Upset_Alert, Blowout, Clutch_Win, Comeback]",
        "secondary_tags": ["List", "of", "other", "relevant", "keywords", "e.g.", "LeBron_James", "Buzzer_Beater"]
    }}
    
    Just return the JSON.
    """

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://antigravity.ai"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1, # Deterministic Tagging
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"⚠️ API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Exception: {e}")
        return None

def run():
    print("🏷️ ORACLE LIBRARIAN: Narrative Tagging Protocol")
    
    # 1. Load Existing Library
    input_path = "quant_engine/upset_library_enriched.json"
    if not os.path.exists(input_path):
        print("❌ Library not found.")
        return

    with open(input_path, 'r') as f:
        library = json.load(f)
        
    print(f"📚 Loaded {len(library)} stories from library.")
    
    tagged_library = []
    
    # 2. Process Batch
    for i, item in enumerate(library):
        print(f"[{i+1}/{len(library)}] Tagging: {item['story_headline']}...")
        
        # Skip if already tagged (if updating existing file)
        # For now, just re-tag or check if 'narrative_tags' exists
        if 'narrative_tags' in item:
            tagged_library.append(item)
            continue
            
        tags_json = get_narrative_tags(item)
        
        if tags_json:
            try:
                tags_data = json.loads(tags_json)
                item['narrative_tags'] = tags_data
            except:
                print("❌ JSON Parse Error")
                item['narrative_tags'] = {"primary_tag": "Unknown", "secondary_tags": []}
        else:
             item['narrative_tags'] = {"primary_tag": "Unknown", "secondary_tags": []}
             
        tagged_library.append(item)
        
        # Rate Limit / Politeness
        time.sleep(0.5)
        
        # Save Incrementally
        if i % 10 == 0:
            with open("processed/tagged_library.json", 'w') as f:
                json.dump(tagged_library, f, indent=2)

    # 3. Final Save
    with open("processed/tagged_library.json", 'w') as f:
        json.dump(tagged_library, f, indent=2)
    
    print("✅ Tagging Complete. Saved to processed/tagged_library.json")

if __name__ == "__main__":
    run()
