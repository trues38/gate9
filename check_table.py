import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
    exit(1)

supabase = create_client(url, key)

try:
    print("🔍 Checking 'ingest_news'...")
    res = supabase.table("ingest_news").select("count", count="exact").limit(1).execute()
    print(f"✅ 'ingest_news' exists. Count: {res.count}")
except Exception as e:
    print(f"⚠️ 'ingest_news' error: {e}")
    try:
        print("🔍 Checking 'global_news_all'...")
        res = supabase.table("global_news_all").select("count", count="exact").limit(1).execute()
        print(f"✅ 'global_news_all' exists. Count: {res.count}")
    except Exception as e2:
        print(f"❌ 'global_news_all' error: {e2}")
