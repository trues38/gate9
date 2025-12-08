import sys
import os
import json
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

load_dotenv(override=True)

TEST_CASES = [
    "Credit Suisse Collapses, Files for Bankruptcy. Global banking giant Credit Suisse announces insolvency.",
    "China Launches Full-Scale Invasion of Taiwan. Beijing announces military operation.",
    "US Inflation Surges to 10.5%, New Record High. CPI data shocks analysts.",
    "New York Community Bank (NYCB) Faces Deposit Run. Shares plunge 40%.",
    "New Deadly Virus Strain Detected in Europe. WHO warns of potential pandemic."
]

from g9_macro_factory.engine.meta_rag import check_meta_fail_log

def debug_meta_rag():
    print("🔍 Debugging Meta-RAG Similarity (Python-side)...")
    
    for text in TEST_CASES:
        print(f"\n📝 Query: {text[:50]}...")
        embedding = get_embedding_sync(text)
        
        # Check with low threshold
        match = check_meta_fail_log(embedding, threshold=0.1)
        
        if match:
            print(f"   MATCH: {match.get('origin_pattern_id')} | {match.get('fail_reason')[:30]}... | Score: {match.get('similarity', 'N/A')}")
        else:
            print("   ❌ No matches found (even with threshold 0.1).")

if __name__ == "__main__":
    debug_meta_rag()
