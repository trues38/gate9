import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_zero.engine.rag_retriever import retrieve_relevant_context
from regime_zero.embedding.vectorizer import create_market_prompt

def test_rag_integration():
    print("🧪 Testing RAG Integration...")
    
    # 1. Test Retrieval
    query = "Oil prices are rising but dollar is weak"
    print(f"\n🔍 Query: {query}")
    context = retrieve_relevant_context(query)
    print(f"📄 Retrieved Context:\n{context}")
    
    # 2. Test Prompt Creation
    market_data = {"Oil": {"value": 80, "z_score": 1.5}, "Dollar": {"value": 100, "z_score": -1.0}}
    headlines = ["Oil surges", "Dollar drops"]
    
    prompt = create_market_prompt("2025-12-02", market_data, headlines, rag_context=context)
    
    if "Historical Patterns & Strategies (RAG)" in prompt:
        print("\n✅ RAG Context successfully injected into prompt.")
    else:
        print("\n❌ RAG Context missing from prompt.")
        
    print("\n--- Prompt Preview ---")
    print(prompt)

if __name__ == "__main__":
    test_rag_integration()
