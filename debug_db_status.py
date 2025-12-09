import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Env vars missing")
    exit(1)

supabase: Client = create_client(url, key)

response = supabase.table("admin_system_status").select("*").order("id", desc=True).limit(1).execute()

if response.data:
    row = response.data[0]
    print(f"ID: {row.get('id')}")
    print(f"LAST_RUN_LOG TYPE: {type(row.get('last_run_log'))}")
    print("--- CONTENT ---")
    print(row.get('last_run_log'))
else:
    print("No data found in table.")
