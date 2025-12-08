import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def check_date(date_str):
    print(f"🔍 Checking data for {date_str}...")
    
    # Check News (using published_at range for the day)
    start = f"{date_str}T00:00:00"
    end = f"{date_str}T23:59:59"
    
    try:
        news = supabase.table("ingest_news").select("count", count="exact")\
            .gte("published_at", start)\
            .lte("published_at", end)\
            .execute()
        print(f"  - News Count: {news.count}")
    except Exception as e:
        print(f"  - News Error: {e}")
    
    # Check Prices (KS11) - ingest_prices has 'date' column as per schema
    try:
        prices = supabase.table("ingest_prices").select("close")\
            .eq("date", date_str)\
            .eq("ticker", "^KS11")\
            .execute()
        print(f"  - KS11 Price: {prices.data}")
    except Exception as e:
        print(f"  - Prices Error: {e}")

if __name__ == "__main__":
    check_date("2024-11-12")
    check_date("2023-11-12") # Just in case
