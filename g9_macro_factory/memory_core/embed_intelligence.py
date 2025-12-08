import os
import sys
import json
import time
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

def embed_missing_intelligence(limit=100):
    """
    Fetches records from g9_intelligence_core where embedding is NULL,
    generates embeddings, and updates them.
    """
    supabase = get_supabase_client()
    
    print(f"🔍 Checking for records missing embeddings (Limit: {limit})...")
    
    try:
        # Fetch records with null embedding
        res = supabase.table("g9_intelligence_core")\
            .select("id, target_date, ticker, macro_env, pattern_id, final_logic")\
            .is_("embedding", "null")\
            .limit(limit)\
            .execute()
            
        records = res.data
        if not records:
            print("✅ All records have embeddings.")
            return

        print(f"🚀 Found {len(records)} records to embed.")
        
        for i, record in enumerate(records):
            print(f"   [{i+1}/{len(records)}] Embedding {record['ticker']} ({record['target_date']})...")
            
            macro_str = json.dumps(record.get("macro_env", {}), sort_keys=True)
            embed_text = f"""
            Date: {record.get('target_date')}
            Ticker: {record.get('ticker')}
            Macro: {macro_str}
            Pattern: {record.get('pattern_id')}
            Logic: {record.get('final_logic')}
            """
            
            try:
                embedding = get_embedding_sync(embed_text)
                
                # Update record
                supabase.table("g9_intelligence_core")\
                    .update({"embedding": embedding})\
                    .eq("id", record['id'])\
                    .execute()
                    
                print("      ✅ Saved.")
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                time.sleep(1) # Backoff
                
    except Exception as e:
        print(f"❌ Error fetching records: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Embed Missing Intelligence")
    parser.add_argument("--limit", type=int, default=50, help="Number of records to process")
    args = parser.parse_args()
    
    embed_missing_intelligence(limit=args.limit)
