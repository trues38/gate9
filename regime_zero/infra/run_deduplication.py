import os
import sys
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def run_deduplication():
    print("🚀 Starting Safe Deduplication...")
    
    # 1. Fetch all IDs and URLs (Chunked if necessary, but let's try full fetch first)
    print("   📥 Fetching metadata...")
    try:
        # Supabase limit is usually 1000. We need to paginate.
        all_rows = []
        start = 0
        batch_size = 1000
        
        while True:
            response = supabase.table("ingest_news").select("id, url, created_at").range(start, start + batch_size - 1).execute()
            rows = response.data
            if not rows:
                break
            all_rows.extend(rows)
            start += batch_size
            print(f"      Fetched {len(all_rows)} rows...", end="\r")
            
        print(f"\n   ✅ Total rows fetched: {len(all_rows)}")
        
        if not all_rows:
            print("   ⚠️ No data found.")
            return

        # 2. Process in Pandas
        df = pd.DataFrame(all_rows)
        
        # Sort by URL and Created At (Newest first)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df.sort_values(by=['url', 'created_at'], ascending=[True, False])
        
        # Identify duplicates
        # keep='first' marks duplicates as True (except the first occurrence)
        duplicates = df[df.duplicated(subset=['url'], keep='first')]
        
        ids_to_delete = duplicates['id'].tolist()
        count = len(ids_to_delete)
        
        print(f"   🔍 Found {count} duplicate rows to delete.")
        
        if count == 0:
            print("   ✨ No duplicates found!")
            return

        # 3. Delete in Batches
        print("   🗑️ Deleting duplicates in batches of 100...")
        
        delete_batch_size = 100
        for i in range(0, count, delete_batch_size):
            batch_ids = ids_to_delete[i:i+delete_batch_size]
            try:
                supabase.table("ingest_news").delete().in_("id", batch_ids).execute()
                print(f"      Deleted {min(i + delete_batch_size, count)} / {count}", end="\r")
            except Exception as e:
                print(f"\n      ❌ Error deleting batch: {e}")
                
        print(f"\n   🎉 Cleanup Complete! Deleted {count} rows.")
        print("   👉 Now you can run the SQL to add the UNIQUE constraint.")

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")

if __name__ == "__main__":
    run_deduplication()
