import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from utils.embedding import get_embedding_sync

def retrieve_relevant_context(query_text, limit=3, threshold=0.7):
    """
    Retrieves relevant strategies and patterns from Supabase based on semantic similarity.
    """
    print(f"🔍 [RAG] Retrieving context for: {query_text[:50]}...")
    
    # 1. Generate Embedding
    embedding = get_embedding_sync(query_text)
    if not embedding:
        print("⚠️ Failed to generate embedding for RAG query.")
        return ""
        
    context_parts = []
    
    # 2. Query Patterns
    try:
        # Using Supabase pgvector RPC 'match_documents' or similar if defined.
        # Since we just created tables, we might not have the RPC function 'match_patterns'.
        # We need to define the RPC function in SQL to do the vector search.
        # IF we can't define RPC, we can't do vector search easily via client-side unless we fetch all (bad).
        
        # Let's assume we need to create the RPC function first.
        # But for now, let's try to use a standard name or check if we can add it.
        
        # If we can't run DDL, we can't add RPC.
        # Let's try to run the search via a raw SQL query using the `run_sql` helper we found!
        from utils.supabase_client import run_sql
        
        # Vector search query
        # Note: vector syntax '[...]'
        vector_str = str(embedding)
        
        sql_pattern = f"""
        SELECT name, description, 1 - (embedding <=> '{vector_str}') as similarity
        FROM rag_patterns
        WHERE 1 - (embedding <=> '{vector_str}') > {threshold}
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        patterns = run_sql(sql_pattern)
        print(f"🐛 [DEBUG] Patterns Result: {patterns}")
        
        if patterns and isinstance(patterns, list):
            for p in patterns:
                if isinstance(p, dict) and 'name' in p:
                    context_parts.append(f"Similar Historical Pattern: {p['name']} ({p['description']})")
                else:
                    print(f"⚠️ Unexpected pattern format: {p}")
                
        # 3. Query Strategies
        sql_strategy = f"""
        SELECT name, content, 1 - (embedding <=> '{vector_str}') as similarity
        FROM rag_strategies
        WHERE 1 - (embedding <=> '{vector_str}') > {threshold}
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        strategies = run_sql(sql_strategy)
        print(f"🐛 [DEBUG] Strategies Result: {strategies}")
        
        if strategies and isinstance(strategies, list):
            for s in strategies:
                if isinstance(s, dict) and 'name' in s:
                    context_parts.append(f"Recommended Strategy: {s['name']} - {s['content']}")
                else:
                    print(f"⚠️ Unexpected strategy format: {s}")
                
    except Exception as e:
        print(f"⚠️ RAG Retrieval Error: {e}")
        
    if not context_parts:
        return "No specific historical patterns or strategies found."
        
    return "\n".join(context_parts)

if __name__ == "__main__":
    # Test
    print(retrieve_relevant_context("Oil prices are rising but dollar is weak"))
