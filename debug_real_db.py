그냥 import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env
load_dotenv(override=True)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"🔌 Connecting to {url}...")
supabase = create_client(url, key)

# 1. Check ingest_news date range
try:
    print("📊 Checking 'ingest_news' date range...")
    min_res = supabase.table("ingest_news").select("published_at").order("published_at", desc=False).limit(1).execute()
    max_res = supabase.table("ingest_news").select("published_at").order("published_at", desc=True).limit(1).execute()
    
    min_date = min_res.data[0]['published_at'] if min_res.data else "None"
    max_date = max_res.data[0]['published_at'] if max_res.data else "None"
    
    print(f"   📅 News Range: {min_date} ~ {max_date}")
    
    # Count 2024
    count_2024 = supabase.table("ingest_news").select("id", count="exact").gte("published_at", "2024-01-01").limit(1).execute()
    print(f"   📰 2024 News Count: {count_2024.count}")

except Exception as e:
    print(f"   ❌ Failed to query ingest_news: {e}")

# 2. Run Preprocessor for one day
print("\n⚙️ Running DailyPreprocessor for 2024-01-04 (US)...")
try:
    from g9_macro_factory.engine.daily_preprocessor import DailyPreprocessor
    processor = DailyPreprocessor()
    
    # Fetch headlines manually to see
    headlines = processor._fetch_headlines("2024-01-04", "US")
    print(f"   📰 Fetched {len(headlines)} headlines.")
    
    # Run process
    success = processor.process("2024-01-04", "US")
    print(f"   🏁 Process Result: {success}")
    
    # Check if it exists now
    res = supabase.table("preprocess_daily").select("*").eq("date", "2024-01-04").eq("country", "US").execute()
    if res.data:
        print(f"   ✅ Data found in DB: {len(res.data)} row(s)")
        print(f"   📄 Sample: {str(res.data[0])[:100]}...")
    else:
        print("   ❌ Data NOT found in DB after process!")

except Exception as e:
    print(f"   ❌ Preprocessor Error: {e}")
