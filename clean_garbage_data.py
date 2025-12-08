from utils.supabase_client import run_sql
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_garbage():
    print("🧹 Cleaning Garbage Data from 'global_news_all'...")
    
    # 1. Reset 'Google News' garbage
    # We look for summaries that contain "Google News" and are very short, or specific error phrases
    
    # Actually, we can just reset ANY row where summary contains "Google News" and length is < 200
    # But SQL 'length' function might vary.
    # Let's just reset rows where summary LIKE '%Google News%' AND summary_status = 'COMPLETED'
    
    while True:
        print(f"🔍 Fetching garbage rows (Server-Side Filter)...")
        
        # Construct OR filter for Supabase
        # Syntax: column.operator.value,column.operator.value
        # We use ilike for case-insensitive matching
        
        patterns = [
            "summary.ilike.%Google News%",
            "summary.ilike.%구글 뉴스%",
            "summary.ilike.%기사 내용%",
            "summary.ilike.%제공된 텍스트%",
            "summary.ilike.%Article Text%",
            "summary.ilike.%뉴스 집계 플랫폼%",
            "summary.ilike.%2002년 출시%",
            "raw_text.ilike.%Google News%"
        ]
        or_filter = ",".join(patterns)
        
        # Also handle short text separately if possible, but for now let's focus on patterns
        # We can't easily mix OR with length check in one go without raw SQL, 
        # but we can do the pattern check first.
        
        try:
            res = supabase.table('global_news_all')\
                .select('id')\
                .eq('summary_status', 'COMPLETED')\
                .or_(or_filter)\
                .limit(1000)\
                .execute()
        except Exception as e:
            print(f"❌ Fetch failed: {e}")
            break
            
        garbage_ids = [item['id'] for item in res.data]
        
        # Also fetch short text rows separately (if patterns didn't catch them)
        # Supabase doesn't support length() filter easily in REST.
        # So we rely on the client-side check for length, but we need to iterate differently.
        # Actually, let's just clean the pattern-matched ones first.
        
        if not garbage_ids:
            print("✨ No more pattern-matched garbage found.")
            break
            
        print(f"🗑️ Found {len(garbage_ids)} garbage rows. Cleaning...")
        
        # Update in batches
        batch_size = 100
        for i in range(0, len(garbage_ids), batch_size):
            batch = garbage_ids[i:i+batch_size]
            try:
                supabase.table('global_news_all')\
                    .update({'summary_status': 'SKIPPED', 'summary': None, 'raw_text': None})\
                    .in_('id', batch)\
                    .execute()
            # Check Raw Text
            if "Google News" in r or len(r) < 500:
                is_garbage = True
                print(f"   - Cleaned batch {i//batch_size + 1} ({len(batch)} rows)")
            except Exception as e:
                print(f"   ❌ Batch failed: {e}")
                
    print("✅ Cleanup Complete.")

if __name__ == "__main__":
    clean_garbage()
