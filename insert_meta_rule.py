import sys
import os
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

def insert_covid_rule():
    print("💉 Injecting COVID-19 Failure Rule into Meta-RAG...")
    supabase = get_supabase_client()
    
    # Rule Details
    event = "WHO Declares COVID-19 Pandemic"
    summary = "Breaking news: WHO Declares COVID-19 Pandemic. Markets react to major development."
    pattern_id = "P-041" # Pandemic
    regime = "LIQUIDITY_CRISIS"
    fail_reason = "Engine chose BUY but market moved -12.52%."
    correction_rule = "Liquidity Crisis(시스템 위기) 때는 BUY_THE_DIP 금지. WAIT_FOR_STABILIZATION."
    
    # Embedding
    full_text = f"{event}. {summary}"
    embedding = get_embedding_sync(full_text)
    
    data = {
        "origin_pattern_id": pattern_id,
        "fail_reason": fail_reason,
        "correction_rule": correction_rule,
        "regime_context": regime,
        "embedding": embedding
    }
    
    try:
        supabase.table("g9_meta_rag").insert(data).execute()
        print("✅ Successfully inserted COVID Rule.")
    except Exception as e:
        print(f"❌ Failed to insert: {e}")

if __name__ == "__main__":
    insert_covid_rule()
