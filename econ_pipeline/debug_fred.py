import os
from pathlib import Path
from dotenv import load_dotenv
import pandas_datareader.data as web
from datetime import datetime

# 1. Load Env
env_path = Path(__file__).parent / '.env'
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

fred_key = os.getenv("FRED_API_KEY")

# 2. Check Key
if not fred_key:
    print("ERROR: FRED_API_KEY not found in environment variables.")
else:
    print(f"SUCCESS: Found FRED_API_KEY (Length: {len(fred_key)})")
    print(f"Key starts with: {fred_key[:4]}...")

# 3. Test API Call
if fred_key:
    print("\nAttempting to fetch CPI data from FRED...")
    try:
        df = web.DataReader("CPIAUCSL", "fred", "2023-01-01", "2023-02-01", api_key=fred_key)
        print("SUCCESS: Fetched data!")
        print(df.head())
    except Exception as e:
        print(f"FAILURE: API Call failed: {e}")
