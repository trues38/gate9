
import json
import os
import time
from openai import OpenAI
from tqdm import tqdm

# Config
INPUT_TAGGED_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_tagged.json"
OUTPUT_VECTOR_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_vectors.json"

# API Setup
MODEL_NAME = "openai/text-embedding-3-small"
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    print("Warning: API Key not found.")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

def get_embedding(text):
    text = text.replace("\n", " ")
    # Truncate to reasonable length to avoid token limits (8191 for ada-002/small)
    # Approx 6000 words safe limit
    if len(text) > 20000: 
        text = text[:20000]
        
    try:
        response = client.embeddings.create(
            input=[text],
            model=MODEL_NAME
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        # Retry once
        time.sleep(2)
        try:
            response = client.embeddings.create(
                input=[text],
                model=MODEL_NAME
            )
            return response.data[0].embedding
        except Exception as e2:
            print(f"Retry failed: {e2}")
            return None

def vectorize_upsets():
    if not os.path.exists(INPUT_TAGGED_JSON):
        print("Input file not found. Wait for tagging to finish.")
        return

    with open(INPUT_TAGGED_JSON, 'r') as f:
        data = json.load(f)

    vectors = []
    print(f"Vectorizing {len(data)} upset stories using {MODEL_NAME}...")

    success_count = 0
    for entry in tqdm(data):
        game_id = entry['game_id']
        headline = entry.get('story_headline', '')
        body = entry.get('story_body', '')
        
        # Combine text for embedding
        # We emphasize the headline and the reasoning if available, then the body
        reasoning = ""
        if 'cause_classification' in entry and entry['cause_classification']:
             reasoning = entry['cause_classification'].get('reasoning', '')
        
        full_text = f"Headline: {headline}. Cause: {reasoning}. Body: {body}"
        
        embedding = get_embedding(full_text)
        
        if embedding:
            vectors.append({
                "game_id": game_id,
                "vector": embedding
            })
            success_count += 1
        
        # Rate limit friendliness (OpenRouter might have limits)
        time.sleep(0.1)

    with open(OUTPUT_VECTOR_JSON, 'w') as f:
        json.dump(vectors, f)
    
    print(f"Vectorized {success_count}/{len(data)} upsets. Saved to {OUTPUT_VECTOR_JSON}")

if __name__ == "__main__":
    vectorize_upsets()
