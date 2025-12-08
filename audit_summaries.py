import os
from supabase import create_client
from dotenv import load_dotenv
import random

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def audit_summaries():
    print("🕵️ Auditing Summary Quality...")
    
    # 1. Stats (Skipped due to timeout)
    print("   (Skipping exact counts due to table size)")

    # 2. Fetch "Good" Examples
    print(f"\n🔍 Fetching VALID examples (excluding garbage)...")
    
    # We can't easily do "NOT LIKE" for many patterns in REST.
    # So we fetch a batch of COMPLETED and filter in Python.
    
    # Try to fetch OLDEST 100 rows (maybe they are valid?)
    try:
        res = supabase.table('global_news_all')\
            .select('id, title, summary, raw_text, url, summary_status')\
            .order('created_at', desc=False)\
            .limit(100)\
            .execute()
            
        print(f"   - Fetched {len(res.data)} rows.")
        
        garbage_phrases = [
            "Google News", "구글 뉴스", "기사 내용", "제공된 텍스트", "Article Text",
            "뉴스 집계 플랫폼", "2002년 출시", "기사 내용 부재", "기사 내용 부족",
            "요약 불가"
        ]
        
        valid_samples = []
        stats = {"PENDING": 0, "SKIPPED": 0, "COMPLETED_GARBAGE": 0, "COMPLETED_VALID": 0, "OTHER": 0}
        
        for item in res.data:
            status = item.get('summary_status', 'UNKNOWN')
            s = item.get('summary', '') or ""
            r = item.get('raw_text', '') or ""
            
            if status == 'PENDING':
                stats['PENDING'] += 1
                continue
            elif status == 'SKIPPED':
                stats['SKIPPED'] += 1
                continue
            elif status == 'COMPLETED':
                is_garbage = False
                if any(phrase in s for phrase in garbage_phrases):
                    is_garbage = True
                if len(r) < 500:
                    is_garbage = True
                    
                if is_garbage:
                    stats['COMPLETED_GARBAGE'] += 1
                else:
                    stats['COMPLETED_VALID'] += 1
                    valid_samples.append(item)
            else:
                stats['OTHER'] += 1

        print(f"   - Batch Stats: {stats}")
                
        if not valid_samples:
            print("⚠️ WARNING: No valid summaries found in this batch!")
        else:
            print(f"✅ Found {len(valid_samples)} valid samples in batch. Showing top 3:")
            for i, item in enumerate(valid_samples[:3]):
                print(f"\n--- [Example {i+1}] ---")
                print(f"Title: {item.get('title')}")
                print(f"URL: {item.get('url')}")
                print(f"Raw Text Len: {len(item.get('raw_text', ''))}")
                print(f"Summary:\n{item.get('summary')[:300]}...") # Truncate for display
                
    except Exception as e:
        print(f"❌ Fetch failed: {e}")

if __name__ == "__main__":
    audit_summaries()
