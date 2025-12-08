import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_clean_title():
    print("🧹 Resetting clean_title to title...")
    
    # We can't do a bulk update with column reference in Supabase-py easily without raw SQL or stored procedure.
    # But we can iterate or use a raw SQL call if enabled.
    # Since I don't have raw SQL access via this client easily, I'll fetch and update in batches.
    # Actually, let's try to use the RPC if available, or just iterate.
    # Iterating might be slow but safer.
    
    # Fetch all items where clean_title != title (if possible) or just all items.
    # Let's just fetch recent items (last 3 days) as that's what matters for the dashboard.
    
    print("   Fetching recent items...")
    response = supabase.table("ingest_news").select("id, title, clean_title").limit(1000).order("published_at", desc=True).execute()
    
    count = 0
    for row in response.data:
        if row['clean_title'] != row['title']:
            try:
                supabase.table("ingest_news").update({"clean_title": row['title']}).eq("id", row['id']).execute()
                count += 1
                if count % 50 == 0:
                    print(f"   Fixed {count} items...")
            except Exception as e:
                print(f"Error updating {row['id']}: {e}")
                
    print(f"✨ Fixed {count} items total.")

if __name__ == "__main__":
    fix_clean_title()
