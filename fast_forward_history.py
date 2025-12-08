import os
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fast_forward_history():
    print("⏩ Fast-Forwarding History (Title -> Summary)...")
    
    total_processed = 0
    batch_size = 1000
    
    while True:
        print(f"🔍 Fetching PENDING rows (Limit {batch_size})...")
        
        try:
            # Fetch PENDING rows (Oldest First)
            res = supabase.table('global_news_all')\
                .select('id, title, published_at')\
                .eq('summary_status', 'PENDING')\
                .order('published_at', desc=False)\
                .limit(batch_size)\
                .execute()
                
            items = res.data
            if not items:
                print("✨ No more PENDING rows found. History is up to date!")
                break
                
            print(f"📦 Processing batch of {len(items)} rows...")
            
            # Prepare batch updates
            # We can't do a single bulk update with different values easily in Supabase REST without RPC.
            # But we can iterate and update, or use `upsert` if we have all fields.
            # Since we only want to update summary/status, iterating is safer but slower.
            # Wait, we can use `upsert` if we include ID. But we need to be careful not to overwrite other fields.
            # Actually, for speed, we can use a loop with `update`.
            
            # Optimization: If we just want to set summary = title, we can't do `update summary = title` in REST.
            # We have to do it client-side.
            
            updates = []
            for item in items:
                updates.append({
                    'id': item['id'],
                    'summary': item['title'], # Use Title as Summary
                    'raw_text': item['title'], # Save Title in raw_text too (for embedding)
                    'summary_status': 'COMPLETED'
                })
                
            # Bulk Upsert is faster
            # Note: Upsert requires all non-nullable fields or default values. 
            # Assuming other fields are nullable or have defaults.
            # If `upsert` fails, we fall back to loop.
            
            try:
                # Upserting only modified fields might work if ID matches
                data = supabase.table('global_news_all').upsert(updates).execute()
                count = len(data.data)
                total_processed += count
                print(f"   ✅ Fast-forwarded {count} rows. (Total: {total_processed})")
            except Exception as e:
                print(f"   ⚠️ Bulk upsert failed: {e}. Trying iterative update...")
                # Fallback
                for up in updates:
                    supabase.table('global_news_all').update(up).eq('id', up['id']).execute()
                total_processed += len(updates)
                print(f"   ✅ Iterative update complete. (Total: {total_processed})")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5) # Wait and retry
            
    print("🎉 Fast-Forward Complete.")

if __name__ == "__main__":
    fast_forward_history()
