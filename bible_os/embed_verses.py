import os
import duckdb
from openai import OpenAI
from dotenv import load_dotenv
import time

# Load env from parent directory
load_dotenv("../.env")

DB_PATH = "./data/db/bible.duckdb"
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None

if not API_KEY:
    raise ValueError("No API Key found. Please set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# Model
MODEL = "text-embedding-3-small" 
# Use OpenRouter specific model name if needed, usually openai/text-embedding-3-small works
# If using pure OpenAI, text-embedding-3-small.

def get_embeddings(texts, model=MODEL):
    # OpenRouter might require specific model naming
    # We'll try generic first.
    try:
        # Note: OpenRouter embedding support varies. 
        # If this fails, we might need to use a different provider or check docs.
        # Assuming user has access to openai/text-embedding-3-small via OpenRouter
        response = client.embeddings.create(
            input=texts,
            model="openai/text-embedding-3-small" if BASE_URL else "text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return []

def main():
    con = duckdb.connect(DB_PATH)
    
    # Check if we need to add column? It was added in ingest_parallel.py
    
    # Get untagged verses
    print("Fetching verses to embed...")
    # verses = con.execute("SELECT id, text_kjv FROM verses WHERE embedding IS NULL").fetchall()
    # For testing, let's limit to 100 first to verify
    verses = con.execute("SELECT id, text_kjv FROM verses WHERE embedding IS NULL").fetchall()
    
    print(f"Found {len(verses)} verses to embed.")
    
    BATCH_SIZE = 100
    total_embedded = 0
    
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i:i+BATCH_SIZE]
        texts = [v[1] for v in batch]
        ids = [v[0] for v in batch]
        
        # Simple retry
        embeddings = []
        for attempt in range(3):
            embeddings = get_embeddings(texts)
            if embeddings:
                break
            time.sleep(2)
            
        if not embeddings:
            print(f"Failed to get embeddings for batch starting at {i}. Skipping.")
            continue
            
        # Update DB
        updates = list(zip(embeddings, ids))
        con.executemany("UPDATE verses SET embedding = ? WHERE id = ?", updates)
        
        total_embedded += len(updates)
        print(f"Embedded {total_embedded}/{len(verses)}")
        
        # Rate limit gentle pause
        time.sleep(0.1)

    print("Embedding complete.")
    con.close()

if __name__ == "__main__":
    main()
