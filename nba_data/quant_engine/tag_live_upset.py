
import json
import os
from openai import OpenAI

# Config
INPUT_FILE = "/Users/js/g9/nba_data/quant_engine/story_upset_2025.json"
OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine/upset_2025_tagged.json"
MODEL_NAME = "deepseek/deepseek-v3.2" # Using V3.2 as per previous successful runs

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def tag_upset():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        story = json.load(f)

    prompt = f"""
    You are an expert NBA analyst. Analyze the following upset story where the underdog {story['underdog']} defeated the favorite {story['favorite']}.
    
    Headline: {story['headline']}
    Body: {story['body']}
    
    Classify the MAIN cause of this upset into exactly ONE of these categories:
    1. The Sleeping Giant (Underdog is actually a good team underperforming)
    2. The Hot Hand (Underdog shot unsustainably well)
    3. The Injury/Rest (Favorite was missing key stars or tired)
    4. The Matchup Nightmare (Tactical disadvantage for favorite)
    5. The Schedule Loss (Favorite played too many games recently)
    6. The Internal Friction (Favorite has locker room issues)
    
    Also provide a 'secondary_cause' if applicable (or null), and a 'reasoning' (1-2 sentences explaining why, in English).
    
    Return strict JSON format:
    {{
        "primary_cause": "Category Name",
        "secondary_cause": "Category Name" or null,
        "reasoning": "Explanation..."
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a JSON-only response bot."},
                {"role": "user", "content": prompt}
            ]
        )
        
        content = completion.choices[0].message.content
        # Extract JSON if wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        tag_data = json.loads(content)
        
        # Merge
        story['cause_classification'] = tag_data
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(story, f, indent=2)
            
        print("Success! Tagged Upset.")
        print(json.dumps(tag_data, indent=2))
        
    except Exception as e:
        print(f"Error calling LLM: {e}")

if __name__ == "__main__":
    tag_upset()
