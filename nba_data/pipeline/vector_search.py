import chromadb
import sys
import argparse

# Configuration
CHROMA_DB_DIR = "nba_data/chroma_db"
COLLECTION_NAME = "nba_narratives"

def search_game(game_id, top_k=5):
    print(f"🔧 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)
    
    print(f"🔍 Searching for twins of Game ID: {game_id}...")
    
    # 1. Fetch the target game's embedding
    target = collection.get(ids=[game_id], include=["embeddings", "metadatas", "documents"])
    if not target['ids']:
        print(f"❌ Game ID {game_id} not found in Vector DB.")
        return

    target_embedding = target['embeddings'][0]
    target_doc = target['documents'][0]
    print(f"🎯 Target Narrative: {target_doc}\n")
    
    # 2. Query for similar games
    results = collection.query(
        query_embeddings=[target_embedding],
        n_results=top_k + 1, # +1 because it will find itself
        include=["metadatas", "documents", "distances"]
    )
    
    # 3. Display Results
    print(f"🧬 Top {top_k} Historical Twins found:\n")
    
    ids = results['ids'][0]
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    dists = results['distances'][0] # distance (lower is better for L2, higher for Cosine if using sim)
    # Chroma default is L2. Lower is better. 0 is identical.
    
    for i in range(len(ids)):
        if ids[i] == game_id: continue # Skip self
        
        sim_score = 1 - dists[i] # Rough conversion if using Cosine distance, dependent on metric. 
        # Actually Chroma returns Distance. For Cosine Distance: 0=Same, 1=Opposite.
        # Capability note: Collection was created with "cosine" space in load script? 
        # Wait, I used metadata={"hnsw:space": "cosine"} in load script.
        # So distance = 1 - cosine_similarity. 
        # Similarity = 1 - distance.
        
        similarity = (1 - dists[i]) * 100
        
        print(f"   {i}. Game {ids[i]} (Sim: {similarity:.1f}%)")
        print(f"      Narrative: {docs[i]}")
        # print(f"      Metadata: {metas[i]}")
        print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search for NBA Game Twins")
    parser.add_argument("game_id", help="Game ID to find twins for")
    args = parser.parse_args()
    
    search_game(args.game_id)
