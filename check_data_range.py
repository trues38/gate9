import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_range(table, date_col):
    try:
        min_res = supabase.table(table).select(date_col).order(date_col, desc=False).limit(1).execute()
        max_res = supabase.table(table).select(date_col).order(date_col, desc=True).limit(1).execute()
        
        if min_res.data and max_res.data:
            print(f"📅 {table}: {min_res.data[0][date_col]} ~ {max_res.data[0][date_col]}")
        else:
            print(f"❌ {table}: No data found.")
    except Exception as e:
        print(f"❌ Error checking {table}: {e}")

if __name__ == "__main__":
    check_range("ingest_prices", "date")
    check_range("ingest_news", "published_at")
