import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def inspect_schema():
    print("🔍 Inspecting ingest_news schema...")
    
    response = supabase.table("ingest_news").select("*").limit(1).execute()
    if response.data:
        row = response.data[0]
        print("Columns found:")
        for key in row.keys():
            print(f"  - {key}")
    else:
        print("No data found to inspect.")

if __name__ == "__main__":
    inspect_schema()
