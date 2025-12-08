import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def archive_old_news(days=30):
    print(f"📦 ARCHIVE NEWS (Older than {days} days) [{datetime.now()}]")
    
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    print(f"   Cutoff Date: {cutoff_date}")
    
    print(f"   Starting batch archive process...")
    
    total_archived = 0
    
    while True:
        # 1. Fetch old news (Batch)
        response = supabase.table("ingest_news") \
            .select("*") \
            .lt("published_at", cutoff_date) \
            .limit(1000) \
            .execute()
            
        rows = response.data
        if not rows:
            print("   ✅ No more old news to archive.")
            break

        # 2. Insert into archive
        ids_to_delete = []
        batch_data = []
        
        for row in rows:
            try:
                archive_data = row.copy()
                del archive_data['id'] # Let archive table generate new ID
                archive_data['archived_at'] = datetime.now().isoformat()
                batch_data.append(archive_data)
                ids_to_delete.append(row['id'])
            except Exception as e:
                print(f"      ⚠️ Prep Error for ID {row['id']}: {e}")

        if batch_data:
            try:
                # Bulk upsert (ignore duplicates)
                # on_conflict="url" ensures we don't create duplicates. 
                # ignore_duplicates=True means if it exists, do nothing (don't update).
                supabase.table("news_archive").upsert(batch_data, on_conflict="url", ignore_duplicates=True).execute()
                
                # Bulk delete from ingest_news (since it's now safe in archive)
                supabase.table("ingest_news").delete().in_("id", ids_to_delete).execute()
                
                total_archived += len(batch_data)
                print(f"   📦 Archived (Safe) & Deleted batch of {len(batch_data)} items. (Total: {total_archived})")
                
            except Exception as e:
                print(f"      ❌ Batch Error: {e}")
                # If bulk fails, maybe try one by one? For now, just break to avoid infinite loop of errors
                break
                
    print(f"✨ Archive Complete. Total moved: {total_archived}")

if __name__ == "__main__":
    # Default to 30 days
    archive_old_news(30)
