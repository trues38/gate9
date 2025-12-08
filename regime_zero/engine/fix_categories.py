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

def fix_categories():
    print("🧹 Cleaning up categories...")
    
    # ENERGY -> ECONOMY
    print("   Fixing ENERGY -> ECONOMY...")
    supabase.table("ingest_news").update({"category": "ECONOMY"}).eq("category", "ENERGY").execute()
    
    # GEOPOLITICS -> POLITICS
    print("   Fixing GEOPOLITICS -> POLITICS...")
    supabase.table("ingest_news").update({"category": "POLITICS"}).eq("category", "GEOPOLITICS").execute()
    
    # FINANCE -> ECONOMY
    print("   Fixing FINANCE -> ECONOMY...")
    supabase.table("ingest_news").update({"category": "ECONOMY"}).eq("category", "FINANCE").execute()

    # WORLD -> POLITICS (Maybe?) Let's stick to the requested ones for now.
    
    print("✨ Categories cleaned up!")

if __name__ == "__main__":
    fix_categories()
