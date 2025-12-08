import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

from utils.supabase_client import run_sql

def apply_schema():
    print("🚀 Applying Schema Changes via RPC...")
    with open("create_tables.sql", "r") as f:
        sql_content = f.read()
    
    # Split by semicolon to run statements individually if needed, 
    # but Postgres usually handles multiple statements in one go if the RPC supports it.
    # Let's try sending the whole block first.
    
    try:
        # The RPC usually returns a result, but for DDL it might return null or empty.
        result = run_sql(sql_content)
        print(f"✅ Schema Applied. Result: {result}")
    except Exception as e:
        print(f"❌ Error applying schema: {e}")

if __name__ == "__main__":
    apply_schema()
