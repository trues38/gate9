
import chromadb
import os
import sys

# Load Env for DeepSeek (just in case, though not needed for Chroma count)
# ...

def debug_chroma():
    print("🕵️‍♂️ Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="chroma_db")
    
    try:
        # Get collection in raw mode
        collection = client.get_collection("nba_narratives")
        count = collection.count()
        print(f"✅ Collection 'nba_narratives' found. Total Items: {count}")
        
        # Test Query for a G-game scenario
        query_text = "Matchup: New Orleans Pelicans vs Orlando Magic. Flow: UP. Fatigue: NORMAL."
        
        print(f"\n🧪 Generating Embedding for: '{query_text}'")
        
        # Use OpenRouter/OpenAI to get 1536-dim embedding
        import openai
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        base_url = "https://openrouter.ai/api/v1"
        
        client_ai = openai.OpenAI(api_key=api_key, base_url=base_url)
        resp = client_ai.embeddings.create(
            input=query_text,
            model="openai/text-embedding-ada-002"
        )
        query_vec = resp.data[0].embedding
        print(f"✅ Embedding Generated. Dimension: {len(query_vec)}")
        
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=3,
            include=['metadatas', 'documents', 'distances']
        )
        
        print("\n🔎 Retrieval Results:")
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i]
            print(f"--- Result {i+1} (Dist: {dist:.4f}) ---")
            print(f"Date: {meta.get('date')}")
            print(f"Headline: {meta.get('story_headline')}")
            print(f"Snippet: {doc[:100]}...")
            
    except Exception as e:
        print(f"❌ Error accessing collection: {e}")

if __name__ == "__main__":
    debug_chroma()
