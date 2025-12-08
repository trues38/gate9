import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration
MIGRATION_START_DATE = "2025-11-01" 
MESSY_START_DATE = "2025-11-25" 

def migrate_data():
    print(f"🚀 Starting FAST Migration from 'news_archive_legacy' (Since {MIGRATION_START_DATE})...")
    
    offset = 0
    batch_size = 1000
    total_migrated_raw = 0
    total_restored_good = 0
    
    while True:
        print(f"   📥 Fetching batch at offset {offset}...")
        
        try:
            # Use range based pagination on the filtered set
            response = supabase.table("news_archive_legacy") \
                .select("*") \
                .gt("created_at", MIGRATION_START_DATE) \
                .order("created_at", desc=False) \
                .range(offset, offset + batch_size - 1) \
                .execute()
                
            rows = response.data
            if not rows:
                break
                
            raw_batch = []
            good_batch = []
            
            for row in rows:
                row_date = row.get('published_at') or row.get('created_at')
                is_messy = False
                if row_date and row_date >= MESSY_START_DATE:
                    is_messy = True
                
                # Construct Raw Entry
                raw_entry = {
                    "url": row.get('url'),
                    "title": row.get('title'),
                    "country": row.get('country', 'US'),
                    "source": row.get('source', 'Legacy'),
                    "published_at": row.get('published_at'),
                    "fetched_at": row.get('created_at'),
                    "processed": not is_messy, 
                    "raw_data": {
                        "original_summary": row.get('summary'),
                        "migration_note": "Migrated from news_archive_legacy"
                    }
                }
                raw_batch.append(raw_entry)
                
                # Construct Good Entry (Only if NOT messy)
                if not is_messy:
                    good_entry = {
                        "title": row.get('title'),
                        "clean_title": row.get('title'),
                        "url": row.get('url'),
                        "published_at": row.get('published_at'),
                        "country": row.get('country', 'US'),
                        "source": row.get('source', 'Legacy'),
                        "summary": row.get('summary'),
                        "is_refined": True,
                        "importance_score": 5
                    }
                    good_batch.append(good_entry)

            # Bulk Insert Raw
            if raw_batch:
                try:
                    supabase.table("news_raw").upsert(raw_batch, on_conflict="url").execute()
                    total_migrated_raw += len(raw_batch)
                except Exception as e:
                    print(f"      ⚠️ Raw Insert Error: {e}")

            # Bulk Insert Good
            if good_batch:
                try:
                    supabase.table("ingest_news").upsert(good_batch, on_conflict="url").execute()
                    total_restored_good += len(good_batch)
                except Exception as e:
                    print(f"      ⚠️ Good Insert Error: {e}")
            
            offset += len(rows)
            print(f"      ✅ Progress: Raw={total_migrated_raw}, Good={total_restored_good}")
            
            if len(rows) < batch_size:
                break
                
        except Exception as e:
            print(f"❌ Error in batch: {e}")
            # If timeout, maybe try smaller batch?
            break

    print(f"🎉 Migration Complete!")
    print(f"   - Total Raw Backfilled: {total_migrated_raw}")
    print(f"   - Total Good Restored (< {MESSY_START_DATE}): {total_restored_good}")
    print(f"   - Recent Messy Data (to be refined): {total_migrated_raw - total_restored_good}")

if __name__ == "__main__":
    migrate_data()
