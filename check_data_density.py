import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_density():
    decades = [
        ("1970-01-01", "1979-12-31"),
        ("1980-01-01", "1989-12-31"),
        ("1990-01-01", "1999-12-31"),
        ("2000-01-01", "2009-12-31"),
        ("2010-01-01", "2019-12-31"),
        ("2020-01-01", "2025-12-31"),
    ]
    
    print("📊 Checking Data Density by Decade...")
    print(f"{'Decade':<15} | {'Prices':<10} | {'News':<10}")
    print("-" * 40)
    
    for start, end in decades:
        try:
            # Count Prices
            p_res = supabase.table("ingest_prices").select("date", count="exact").gte("date", start).lte("date", end).limit(1).execute()
            p_count = p_res.count
            
            # Count News
            n_res = supabase.table("ingest_news").select("published_at", count="exact").gte("published_at", start).lte("published_at", end).limit(1).execute()
            n_count = n_res.count
            
            print(f"{start[:4]}s{'':<10} | {p_count:<10} | {n_count:<10}")
        except Exception as e:
            print(f"{start[:4]}s: Error {e}")

if __name__ == "__main__":
    check_density()
