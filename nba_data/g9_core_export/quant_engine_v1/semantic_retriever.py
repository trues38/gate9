import os
import chromadb
import logging
from chromadb.utils import embedding_functions

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SemanticRetriever")

class SemanticNarrativeRetriever:
    def __init__(self, db_path="/Users/js/g9/nba_data/chroma_db", collection_name="nba_narratives"):
        """
        Initialize the Semantic Retriever connected to the local Chroma persist directory.
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
        # Initialize Client
        try:
            logger.info(f"🔌 Connecting to ChromaDB at {self.db_path}...")
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Load Collection WITHOUT embedding function (raw mode)
            # This avoids "Function Conflict" errors if the DB was built with a different config
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"✅ Loaded Collection '{self.collection_name}' with count: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Chroma: {e}")

    def find_similar_situations(self, query_text, n_results=5, filter_years=None):
        """
        Find historically similar situations based on a natural language query.
        """
        if not self.collection:
            logger.warning("Search skipped: Collection not loaded.")
            return []

        # Generate Embedding Manually
        import openai
        
        # Try OpenAI First, then OpenRouter
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None
        model_name = "text-embedding-ada-002"
        
        if not api_key:
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                base_url = "https://openrouter.ai/api/v1"
                # OpenRouter usually requires 'openai/' prefix or strict model mapping
                # But let's try standard first, often it maps.
                # Actually for embeddings via OR, we likely need the specific ID.
                # Let's assume user might have put a real OpenAI key in OPENROUTER variable just in case,
                # or we just try to hit the endpoint.
                pass
        
        if not api_key:
             logger.warning("⚠️ No API Key found (OpenAI or OpenRouter). Cannot generate embedding.")
             return []
             
        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            
            # Map model name for OpenRouter if needed
            # Common OpenRouter ID for ada-002 is 'openai/text-embedding-ada-002'
            if base_url:
                target_model = "openai/text-embedding-ada-002"
            else:
                target_model = "text-embedding-ada-002"
                
            resp = client.embeddings.create(input=query_text, model=target_model)
            query_vec = resp.data[0].embedding
            
            results = self.collection.query(
                query_embeddings=[query_vec],
                n_results=n_results
            )
            
            # Format Results
            hits = []
            if results['ids']:
                for i in range(len(results['ids'][0])):
                    hits.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i] if results['documents'] else None,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            return hits

        except Exception as e:
            logger.error(f"⚠️ Search failed: {e}")
            return []

if __name__ == "__main__":
    # Test Run
    retriever = SemanticNarrativeRetriever()
    hits = retriever.find_similar_situations("A star player returning from injury to dominate")
    for h in hits:
        print(f"[{h['distance']:.3f}] {h['document']}")
