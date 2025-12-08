import argparse
import json
import os
import glob
import time
import random
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------
# Constants
# ---------------------------
DATA_DIR = "nba_data"
CHUNK_DIR = os.path.join(DATA_DIR, "stories_chunks")
VECTOR_DIR = os.path.join(DATA_DIR, "stories_vector_tags")

# Load environment variables
load_dotenv("/Users/js/g9/.env")

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Models
EMBEDDING_MODEL = "openai/text-embedding-3-small"  # Reliable & Fast
TAGGING_MODEL = "deepseek/deepseek-v3.2-exp"  # DeepSeek V3.2 Exp ($0.32/M output)


os.makedirs(VECTOR_DIR, exist_ok=True)

# ---------------------------
# Setup Client
# ---------------------------
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY not found in environment variables.")
    print("Please export OPENROUTER_API_KEY='your_key_here'")
    client = None
else:
    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )

# ---------------------------
# 1) Embedding
# ---------------------------
def embed(text: str):
    if not client:
        return [0.0] * 1024 # Failure stub

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error embedding text: {e}")
        time.sleep(2) # Simple backoff
        return [0.0] * 1024

# ---------------------------
# 2) Vector Tag Classification (LLM)
# ---------------------------
def classify_vector_tags(text: str):
    if not client:
        return _get_stub_tags()

    prompt = f"""
    Analyze the following NBA game narrative chunk and extract 'Regime Tags'.
    Output specific JSON only.

    Text Chunk:
    "{text}"

    Required JSON Structure:
    {{
        "NarrativeIntensity": "Low" | "Medium" | "High" | "Extreme",
        "DominantArc": "Comeback" | "Blowout" | "Clutch" | "Injury" | "Rivalry" | "RecordBreaking" | "Neutral",
        "EmotionalTone": "Euphoric" | "Desperate" | "Resilient" | "Frustrated" | "Neutral",
        "GameFlow": "Stable" | "Volatile" | "OneSided" | "BackAndForth",
        "PsychologicalShift": true | false,  // Did momentum shift significantly?
        "PlayerFocus": ["LeBron James", ...] // List main players mentioned in emotional context
    }}
    """

    try:
        response = client.chat.completions.create(
            model=TAGGING_MODEL,
            messages=[
                {"role": "system", "content": "You are a Sports Narrative Analyst. Output valid JSON only. Do not wrap in markdown code blocks."},
                {"role": "user", "content": prompt}
            ],
            # response_format={"type": "json_object"}  <-- CAUSED 400 ERROR on Free Tier
        )
        content = response.choices[0].message.content
        print(f"DEBUG USAGE: {response.usage}") # AUDIT COST
        content = _clean_json_response(content)
        return json.loads(content)
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Rate limit" in err_msg:
            print(f"🚨 CRITICAL RATE LIMIT: {err_msg}")
            print("Stopping execution to prevent data corruption.")
            raise e # Crash the script intentionally
            
        print(f"Error labeling text: {e}")
        time.sleep(2)
        return _get_stub_tags()

def _clean_json_response(content: str) -> str:
    """Removes markdown code blocks if present."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

def _get_stub_tags():
    return {
        "NarrativeIntensity": "Medium",
        "DominantArc": "Neutral",
        "EmotionalTone": "Neutral",
        "GameFlow": "Stable",
        "PsychologicalShift": False,
        "PlayerFocus": []
    }

# ---------------------------
# 3) Process Chunks
# ---------------------------
# ---------------------------
# 3) Process Stories (Whole File Optimization)
# ---------------------------
def process_stories():
    if not client:
        print("CRITICAL: No API Key provided. Running in stub mode.")
        time.sleep(3)

    # Input: Processed Stories (Raw JSONs with 'body')
    files = glob.glob(os.path.join(DATA_DIR, "stories_raw", "*.json"))
    print(f"Found {len(files)} story files to process using {EMBEDDING_MODEL} & {TAGGING_MODEL}.")
    
    # Output Dir (New optimized version)
    optimized_vector_dir = os.path.join(DATA_DIR, "stories_vector_tags_v2")
    os.makedirs(optimized_vector_dir, exist_ok=True)
    
    random.shuffle(files)
    
    processed_count = 0
    
    for path in tqdm(files):
        # DEBUG LIMIT REMOVED
        
        game_id = os.path.basename(path).replace("story_", "").replace(".json", "")
        out_path = os.path.join(optimized_vector_dir, f"{game_id}.jsonl")
        
        if os.path.exists(out_path):
            continue

        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Use 'body' or 'text' depending on source
            text = data.get('body') or data.get('text', "")
            if len(text) < 50: continue # Skip empty stories
            
            # 1. Embed (Whole Story Summary Vector)
            # Truncate to first 2000 chars for embedding to capture "Gist" without token limit risk
            emb_text = text[:8000] 
            emb = embed(emb_text)
            
            # 2. Tag (Whole Story Analysis)
            # LLM can handle full context
            vec_tags = classify_vector_tags(text[:12000]) # Cap at ~3k tokens/12k chars for safety

            out = {
                "game_id": game_id,
                "vector_tags": vec_tags,
                "embedding": emb,
                "source_text_length": len(text)
            }
            
            with open(out_path, 'w') as w:
                w.write(json.dumps(out) + "\n")
                
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing {path}: {e}")
            continue

    print(f"Complete. Processed {processed_count} files via Optimized Pipeline.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Run the pipeline")
    parser.add_argument("--model", type=str, default=TAGGING_MODEL, help="Override tagging model")
    args = parser.parse_args()

    if args.model:
        TAGGING_MODEL = args.model
        print(f"🚀 Overriding Tagging Model: {TAGGING_MODEL}")

    if args.run:
        process_stories()
    else:
        print("Use --run to execute.")
