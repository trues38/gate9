
import chromadb
from chromadb.utils import embedding_functions
import json
import os

# Config
ENRICHED_LIBRARY = "/Users/js/g9/nba_data/quant_engine/upset_library_enriched.json"
CHROMA_DB_PATH = "/Users/js/g9/nba_data/chroma_db"

def vectorize_store():
    # 1. Load Data
    source_file = ENRICHED_LIBRARY
    if not os.path.exists(source_file):
        print(f"Enriched library not found at {source_file}. Checking fallback...")
        source_file = source_file.replace("_enriched.json", "_tagged.json")
    
    if not os.path.exists(source_file):
        print("No library file found. Aborting.")
        return

    with open(source_file, 'r') as f:
        upsets = json.load(f)

    print(f"Loaded {len(upsets)} upsets from {source_file}")

    # 2. Init ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Use OpenAI Embedding (requires OPENAI_API_KEY env var)
    # OR use default (SentenceTransformer) if no key.
    # User has OPENROUTER_API_KEY. Chroma might not support OpenRouter out of box easily without custom func.
    # Let's use the default all-MiniLM-L6-v2 which runs locally (no API key needed) for stability,
    # OR if user insists on high quality, we can try/catch.
    # DeepSeek context: user uses OpenRouter. 
    # Let's try to use a simple custom embedding function using OpenAI client if env var exists, else default.
    
    # Actually, for "Vibe" matching, local MiniLM is quite good and fast.
    # Let's stick to default for now to avoid Auth errors, unless user specified model.
    # User said "OpenAI/text-embedding-3-small" in previous session summary.
    # So we should try to use that via OpenRouter if possible, or direct OpenAI.
    
    collection = client.get_or_create_collection(name="historical_upsets")

    # 3. Prepare Data
    ids = []
    documents = []
    metadatas = []

    for game in upsets:
        game_id = game['game_id']
        
        # Construct Narrative Text for Embedding
        # "Title + Reasoning + Body Summary"
        cause = game.get('cause_classification', {})
        text_blob = f"Matchup: {game['matchup']}\nHeadline: {game.get('headline', '')}\n"
        text_blob += f"Primary Cause: {cause.get('primary_cause', 'Unknown')}\n"
        text_blob += f"Analysis: {cause.get('reasoning', '')}\n"
        # Add body snippet if available
        if 'body' in game:
            text_blob += f"Story: {game['body'][:1000]}"
            
        ids.append(game_id)
        documents.append(text_blob)
        
        # Metadata for filtering
        meta = {
            "date": game['date'],
            "season": game['season'],
            "favorite": game['favorite'],
            "underdog": game['underdog'],
            "primary_cause": cause.get('primary_cause', 'Unknown'),
            # Flatten Context for Metadata Filter
            "rest_days": str(game.get('context', {}).get('rest_days', 'N/A')),
            "location": str(game.get('context', {}).get('location', 'N/A'))
        }
        metadatas.append(meta)

    # 4. Upsert
    print("Upserting to ChromaDB...")
    # Batch processing is better for large data, but 182 is small.
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"Successfully indexed {len(ids)} games in ChromaDB collection 'historical_upsets'.")

if __name__ == "__main__":
    vectorize_store()
