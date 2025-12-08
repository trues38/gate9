import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def list_tickers():
    # Fetch distinct tickers? Supabase doesn't support distinct easily via JS client without RPC.
    # I'll fetch a bunch of rows and set them.
    # Or use a known list.
    # Let's fetch 1000 rows and see.
    res = supabase.table("ingest_prices").select("ticker").limit(2000).execute()
    tickers = set(r['ticker'] for r in res.data)
    print(f"Found Tickers: {tickers}")

if __name__ == "__main__":
    list_tickers()
