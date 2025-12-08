import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def inspect():
    tables = ["ingest_news", "ingest_prices"]
    for t in tables:
        print(f"🔍 Inspecting '{t}'...")
        try:
            res = supabase.table(t).select("*").limit(1).execute()
            if res.data:
                print(f"✅ '{t}' Columns: {list(res.data[0].keys())}")
                print(f"   Sample: {res.data[0]}")
            else:
                print(f"⚠️ '{t}' found but empty.")
        except Exception as e:
            print(f"❌ '{t}' Error: {e}")

if __name__ == "__main__":
    inspect()
