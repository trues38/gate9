
import json
import os
import argparse
import numpy as np
import time
from openai import OpenAI

# Config
TAGGED_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_tagged.json"
VECTOR_JSON = "/Users/js/g9/nba_data/quant_engine/upset_library_vectors.json"

# API Setup
MODEL_NAME = "openai/text-embedding-3-small"
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    print("Warning: API Key not found. Please set OPENROUTER_API_KEY.")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

def get_embedding(text):
    try:
        response = client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=MODEL_NAME
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def find_twins(query, top_k=3):
    print(f"Searching for twins for query: '{query}'...")
    
    # 1. Embed Query
    query_vec = get_embedding(query)
    if not query_vec:
        print("Failed to embed query.")
        return

    # 2. Load Library
    if not os.path.exists(VECTOR_JSON) or not os.path.exists(TAGGED_JSON):
        print("Upset Library files not found. Run build/tag/vectorize steps first.")
        return

    with open(VECTOR_JSON, 'r') as f:
        vectors = json.load(f)
        
    with open(TAGGED_JSON, 'r') as f:
        narratives = {item['game_id']: item for item in json.load(f)}

    # 3. Calculate Similarity
    results = []
    
    # Pre-parse vectors to numpy for speed if needed, but list loop is fine for N=182
    for item in vectors:
        game_id = item['game_id']
        vec = item['vector']
        
        # Skip if vector is None or empty
        if not vec: continue
        
        score = cosine_similarity(query_vec, vec)
        results.append((game_id, score))

    # 4. Sort and Display
    results.sort(key=lambda x: x[1], reverse=True)
    
    output_lines = []
    output_lines.append(f"\nTop {top_k} Historical Twins for '{query}':\n" + "="*60)
    
    for i, (game_id, score) in enumerate(results[:top_k]):
        story = narratives.get(game_id)
        if not story: continue
        
        output_lines.append(f"\n{i+1}. {story['favorite']} vs {story['underdog']} ({story['date']}) | Similarity: {score:.4f}")
        output_lines.append(f"   Headline: {story.get('story_headline')}")
        
        cause = story.get('cause_classification', {})
        output_lines.append(f"   Cause: {cause.get('primary_cause')} / {cause.get('secondary_cause')}")
        output_lines.append(f"   Reasoning: {cause.get('reasoning')}")
    
    final_output = "\n".join(output_lines)
    print(final_output)
    
    with open("twin_results.txt", "w") as f:
        f.write(final_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find Twin Upsets")
    parser.add_argument("query", type=str, help="Description of the current situation")
    parser.add_argument("--top_k", type=int, default=3, help="Number of results to return")
    
    args = parser.parse_args()
    find_twins(args.query, args.top_k)
