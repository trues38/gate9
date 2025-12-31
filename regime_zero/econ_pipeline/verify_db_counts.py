import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load Env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("--- Database Record Counts ---")

# Get unique country/indicator pairs
try:
    # Fetch all distinct country, indicator pairs (using a small trick or just counting groups)
    # Supabase JS client has .rpc() but here we might just fetch all and aggregate in python if small enough, 
    # OR better: iterate through known indicators and count.
    
    indicators = {
        "US": ["CPI", "PCE", "RetailSales", "FOMC"],
        "JP": ["JPYUSD", "BOJ"],
        "CN": ["PMI", "Exports", "Retail", "Policy"],
        "KR": ["Exports", "Retail"]
    }

    total_records = 0
    for country, inds in indicators.items():
        for ind in inds:
            # Count records for this indicator
            res = supabase.table("econ_indicators") \
                .select("id", count="exact") \
                .eq("country", country) \
                .eq("indicator", ind) \
                .execute()
            
            count = res.count
            print(f"[{country}] {ind}: {count} records")
            total_records += count

    print("------------------------------")
    print(f"Total Records: {total_records}")

except Exception as e:
    print(f"Error querying DB: {e}")
