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

def inspect_titles():
    print("🔍 Inspecting recent US news titles...")
    
    response = supabase.table("ingest_news") \
        .select("id, title, title_ko, country, source") \
        .eq("country", "US") \
        .order("published_at", desc=True) \
        .limit(5) \
        .execute()
        
    for row in response.data:
        print(f"ID: {row['id']}")
        print(f"  Country: {row['country']}")
        print(f"  Source: {row['source']}")
        print(f"  Title (Original): {row['title']}")
        print(f"  Title KO: {row['title_ko']}")
        print("-" * 40)

if __name__ == "__main__":
    inspect_titles()
