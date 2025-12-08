import sys
import os
import json

# Add project root to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.embedding import get_embedding_sync

def create_market_prompt(date, market_data, headlines, rag_context=""):
    """
    Combines market data and headlines into a semantic string.
    """
    prompt = f"Market Regime Snapshot for {date}\n\n"
    
    prompt += "## 7 Core Indicators\n"
    for key, data in market_data.items():
        if data:
            prompt += f"- {key.capitalize()}: {data['value']} (Z-Score: {data['z_score']})\n"
        else:
            prompt += f"- {key.capitalize()}: N/A\n"
            
    prompt += "\n## Top Headlines\n"
    for h in headlines[:20]: # Limit to top 20 to avoid noise
        prompt += f"- {h}\n"

    if rag_context:
        prompt += "\n## Historical Patterns & Strategies (RAG)\n"
        prompt += rag_context + "\n"
        
    return prompt

def vectorize_market_state(date, market_data, headlines, rag_context=""):
    """
    Generates the 3072D embedding for the market state.
    """
    prompt = create_market_prompt(date, market_data, headlines, rag_context)
    
    # Truncate to avoid token limits (approx 8k tokens ~ 32k chars, but safe side 20k)
    if len(prompt) > 20000:
        print(f"⚠️ Prompt too long ({len(prompt)} chars). Truncating to 20000.")
        prompt = prompt[:20000]
        
    print(f"🔤 Generating embedding for prompt ({len(prompt)} chars)...")
    
    embedding = get_embedding_sync(prompt)
    return embedding, prompt

if __name__ == "__main__":
    # Test
    from regime_zero.ingest.fetch_market_data import get_market_vector
    from regime_zero.ingest.fetch_headlines import get_daily_headlines
    
    test_date = "2024-11-29" # Use a fixed date for testing
    
    m_data = get_market_vector(test_date)
    headlines = get_daily_headlines(test_date)
    
    vec, prompt = vectorize_market_state(test_date, m_data, headlines)
    print(f"✅ Generated Vector: {len(vec)} dimensions")
    print("--- Prompt Preview ---")
    print(prompt[:500] + "...")
