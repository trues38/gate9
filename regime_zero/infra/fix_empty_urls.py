import os
import sys
import time
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def fix_empty_urls():
    print("🚀 Removing Invalid News (ID-based Iteration)...")
    
    try:
        # Check for start_id argument to resume
        last_id = sys.argv[1] if len(sys.argv) > 1 else None
        if last_id:
            print(f"   🔄 Resuming from ID: {last_id}")

        total_checked = 0
        total_deleted = 0
        
        while True:
            # Retry logic for network stability
            rows = []
            for attempt in range(3):
                try:
                    # Fetch batch of 1000, ordered by ID
                    query = supabase.table("ingest_news").select("id, url").order("id").limit(1000)
                    
                    # Apply keyset pagination if we have a last_id
                    if last_id:
                        query = query.gt("id", last_id)
                        
                    response = query.execute()
                    rows = response.data
                    break # Success
                except Exception as e:
                    print(f"\n      ⚠️ Network Error (Attempt {attempt+1}/3): {e}")
                    time.sleep(2)
                    if attempt == 2: raise e # Fail after 3 attempts

            if not rows:
                break
            
            # Update last_id for next iteration
            last_id = rows[-1]['id']
            total_checked += len(rows)
            
            # Identify invalid URLs
            ids_to_delete = [r['id'] for r in rows if not r.get('url')]
            
            if ids_to_delete:
                # Retry logic for deletion too
                for attempt in range(3):
                    try:
                        supabase.table("ingest_news").delete().in_("id", ids_to_delete).execute()
                        total_deleted += len(ids_to_delete)
                        break
                    except Exception as e:
                        print(f"\n      ⚠️ Delete Error (Attempt {attempt+1}/3): {e}")
                        time.sleep(2)
                
            print(f"   Checked {total_checked} rows | Deleted {total_deleted} invalid | Last ID: {last_id}", end="\r")
            
            # Throttle to be nice to the API
            time.sleep(0.05)
            
        print(f"\n\n   🎉 Cleanup Complete!")
        print(f"      - Total Checked: {total_checked}")
        print(f"      - Total Deleted: {total_deleted}")
        print("   👉 Now try running the SQL constraint again:")
        print("      ALTER TABLE ingest_news ADD CONSTRAINT unique_news_url UNIQUE (url);")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    fix_empty_urls()
