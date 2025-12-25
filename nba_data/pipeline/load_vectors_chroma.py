import chromadb
from chromadb.config import Settings
import json
import os
import glob
from tqdm import tqdm

# Configuration
VECTOR_DIR = "nba_data/stories_vector_tags_v2"
CHROMA_DB_DIR = "nba_data/chroma_db"
COLLECTION_NAME = "nba_narratives"

def load_vectors():
    # 1. Initialize Chroma Client
    print(f"🔧 Initializing ChromaDB at {CHROMA_DB_DIR}...")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # 2. Get or Create Collection
    # Using L2 (Euclidean) distance by default, or Cosine. 
    # Normalized embeddings with Dot Product = Cosine Similarity.
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    print(f"📂 Collection '{COLLECTION_NAME}' ready. Count: {collection.count()}")
    
    # 3. List Files
    files = glob.glob(os.path.join(VECTOR_DIR, "*.jsonl"))
    print(f"📄 Found {len(files)} JSONL files to ingest.")
    
    # 4. Processing Loop
    batch_size = 100
    ids_batch = []
    embeddings_batch = []
    metadatas_batch = []
    documents_batch = []
    
    count = 0
    
    for fpath in tqdm(files, desc="Ingesting Vectors"):
        with open(fpath, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # Extract Fields
                    game_id = data.get("game_id")
                    embedding = data.get("embedding")
                    tags = data.get("vector_tags", {})
                    
                    if not game_id or not embedding:
                        continue
                        
                    # Construct Metadata
                    # Flatten tags for metadata filtering
                    metadata = {
                        "game_id": game_id,
                        "narrative_intensity": tags.get("NarrativeIntensity", "Unknown"),
                        "dominant_arc": tags.get("DominantArc", "Unknown"),
                        "emotional_tone": tags.get("EmotionalTone", "Unknown"),
                        "game_flow": tags.get("GameFlow", "Unknown")
                    }
                    
                    # Construct Document (Text Representation for Hybrid Search)
                    # "Game 00223...: High Intensity, Comeback Arc..."
                    doc_text = f"Game {game_id}: {tags.get('NarrativeIntensity', '')} Intensity, {tags.get('DominantArc', '')} Arc. {tags.get('EmotionalTone', '')} Tone. Flow: {tags.get('GameFlow', '')}."
                    
                    # Add to Batch
                    ids_batch.append(game_id)
                    embeddings_batch.append(embedding)
                    metadatas_batch.append(metadata)
                    documents_batch.append(doc_text)
                    
                    # Flush Batch
                    if len(ids_batch) >= batch_size:
                        collection.upsert(
                            ids=ids_batch,
                            embeddings=embeddings_batch,
                            metadatas=metadatas_batch,
                            documents=documents_batch
                        )
                        count += len(ids_batch)
                        ids_batch, embeddings_batch, metadatas_batch, documents_batch = [], [], [], []
                        
                except Exception as e:
                    print(f"Error parsing line in {fpath}: {e}")
                    
    # Final Flush
    if ids_batch:
        collection.upsert(
            ids=ids_batch,
            embeddings=embeddings_batch,
            metadatas=metadatas_batch,
            documents=documents_batch
        )
        count += len(ids_batch)
        
    print(f"\n✅ Ingestion Complete!")
    print(f"📊 Total Vectors in Collection: {collection.count()} (Added {count} this run)")

if __name__ == "__main__":
    load_vectors()
