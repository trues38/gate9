import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def inspect_table():
    print("🔍 Inspecting 'preprocess_daily'...")
    try:
        # Fetch 1 row to see columns
        res = supabase.table("preprocess_daily").select("*").limit(1).execute()
        with open("schema_info.txt", "w") as f:
            if res.data:
                f.write(f"Columns: {list(res.data[0].keys())}\n")
                f.write(f"Sample: {res.data[0]}\n")
            else:
                f.write("Table is empty or not found.")
    except Exception as e:
        with open("schema_info.txt", "w") as f:
            f.write(f"Error: {e}")

if __name__ == "__main__":
    inspect_table()
