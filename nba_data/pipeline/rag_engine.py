
import chromadb
from chromadb.utils import embedding_functions
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI Client (for manual embedding if needed, or structured usage)
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None

if not API_KEY:
    raise ValueError("No API Key found")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

CHROMA_PATH = "nba_data/chroma_db"
COLLECTION_NAME = "nba_narratives"

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_embedding(text):
    """
    Generate embedding for search query using the same model as ingestion.
    Assumes 'text-embedding-3-small' was used.
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def search_narratives(query, n_results=5):
    """
    Search ChromaDB for relevant narratives.
    """
    chroma_client = get_chroma_client()
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except:
        return []

    # Generate Query Embedding
    query_vec = get_embedding(query)
    
    # Query
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=n_results
    )
    
    # Format Results
    # documents list of list
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    distances = results['distances'][0]
    
    search_hits = []
    for doc, meta, dist in zip(docs, metas, distances):
        search_hits.append({
            "content": doc,
            "meta": meta,
            "distance": dist
        })
        
    return search_hits

def format_rag_context(hits):
    """
    Formats search hits into a context string for LLM.
    """
    if not hits:
        return "No specific narrative details found."
        
    context_lines = []
    for hit in hits:
        # metadata contains 'game_id', 'emotional_tone', etc.
        meta = hit['meta']
        tone = meta.get('emotional_tone', 'Unknown')
        arc = meta.get('dominant_arc', 'General')
        content = hit['content']
        context_lines.append(f"- [{tone}/{arc}] {content}")
        
    return "\n".join(context_lines)

if __name__ == "__main__":
    # Test
    print("Testing RAG Engine...")
    q = "LeBron James recent conflict or injury"
    hits = search_narratives(q, n_results=3)
    print(f"Query: {q}")
    print(format_rag_context(hits))
