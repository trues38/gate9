import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def check_table(table_name):
    try:
        res = supabase.table(table_name).select("*").limit(1).execute()
        print(f"✅ Table '{table_name}' exists.")
        return True
    except Exception as e:
        print(f"❌ Table '{table_name}' check failed: {e}")
        return False

if __name__ == "__main__":
    check_table("news_items")
    check_table("global_news_all")
    check_table("price_daily")
