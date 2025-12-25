

import json
import os
import time
from openai import OpenAI
from tqdm import tqdm

# Config
INPUT_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_raw.json"
OUTPUT_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_tagged.json"

# API Setup
# Prioritize OpenRouter if the model name implies it
MODEL_NAME = "deepseek/deepseek-v3.2" # User requested
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if "/" in MODEL_NAME else "https://api.deepseek.com"

if not API_KEY:
    # Fallback/Debug: check for a local .env file or similar if needed, 
    # but for now assume it's in the environment as the user suggested.
    print("Warning: API Key not found in environment variables.")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

TAXONOMY_PROMPT = """
You are an expert NBA analyst. Analyze the following game summary of a significant upset and assign a cause from the taxonomy below.

**Taxonomy (Select 1 Primary, Optional 1 Secondary):**
1. **The Sleeping Giant** (Favorite complacency, low energy, overlooking opponent)
2. **The Hot Hand** (Underdog shoots unconsciously from 3/field, outlier shooting variance)
3. **The Injury/Rest** (Favorite missing key star or playing back-to-back/tired legs)
4. **The Matchup Nightmare** (Specific tactical disadvantage, e.g., small ball vs bigs, specific player killer)
5. **The Schedule Loss** (3rd game in 4 nights, long road trip fatigue)
6. **The Internal Friction** (Coach/player conflict, chemistry issues visible)

**Input Data**:
- **Headline**: {headline}
- **Context**: Favorite ({favorite}) lost to Underdog ({underdog}).
- **Story**: {body}

**Output Format**:
Return ONLY a valid JSON object with no markdown formatting:
{{
    "primary_cause": "Category Name",
    "secondary_cause": "Category Name" or null,
    "reasoning": "One sentence explanation citing specific text evidence (e.g. 'LeBron sat out' or 'Underdog shot 60% from 3')"
}}
"""

def call_llm(headline, body, favorite, underdog):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a JSON-only NBA analyst helper."},
                {"role": "user", "content": TAXONOMY_PROMPT.format(
                    headline=headline, 
                    body=body[:3000], # Truncate body if too long to save context/prevent errors
                    favorite=favorite, 
                    underdog=underdog
                )}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return {
            "primary_cause": "Unknown",
            "secondary_cause": null,
            "reasoning": f"Error: {str(e)}"
        }

def tag_upsets():
    if not os.path.exists(INPUT_JSON):
        print("Input file not found.")
        return

    with open(INPUT_JSON, 'r') as f:
        data = json.load(f)

    tagged_data = []
    print(f"Tagging {len(data)} upsets using {MODEL_NAME}...")

    # Iterate
    for entry in tqdm(data):
        # Skip if already tagged (optional check, but good for restartability)
        # if 'cause_classification' in entry: continue 
        
        classification = call_llm(
            entry.get('story_headline', ''), 
            entry.get('story_body', ''), 
            entry.get('favorite', ''), 
            entry.get('underdog', '')
        )
        
        entry['cause_classification'] = classification
        tagged_data.append(entry)
        
        # Save incrementally in case of crash
        if len(tagged_data) % 10 == 0:
             with open(OUTPUT_JSON, 'w') as f:
                json.dump(tagged_data + data[len(tagged_data):], f, indent=2)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(tagged_data, f, indent=2)
    
    print(f"Tagged {len(tagged_data)} upsets. Saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    tag_upsets()

