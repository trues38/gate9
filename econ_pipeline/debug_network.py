import os
import socket
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load Env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
print(f"DEBUG: Loaded URL: '{SUPABASE_URL}'")

if not SUPABASE_URL:
    print("ERROR: SUPABASE_URL is empty")
    exit(1)

# Parse Hostname
try:
    parsed = urlparse(SUPABASE_URL)
    hostname = parsed.hostname
    print(f"DEBUG: Hostname: '{hostname}'")
except Exception as e:
    print(f"ERROR: Failed to parse URL: {e}")
    exit(1)

# Test 1: DNS Resolution
print("\n--- Test 1: DNS Resolution ---")
try:
    ip = socket.gethostbyname(hostname)
    print(f"SUCCESS: Resolved {hostname} to {ip}")
except Exception as e:
    print(f"FAILURE: DNS Resolution failed: {e}")

# Test 2: HTTP Request (requests)
print("\n--- Test 2: HTTP Request (requests) ---")
try:
    # Supabase usually returns a 404 or JSON on root, but it proves connectivity
    response = requests.get(SUPABASE_URL, timeout=5)
    print(f"SUCCESS: HTTP {response.status_code}")
except Exception as e:
    print(f"FAILURE: HTTP Request failed: {e}")

# Test 3: Supabase Client
print("\n--- Test 3: Supabase SDK ---")
try:
    from supabase import create_client
    key = os.getenv("SUPABASE_KEY")
    client = create_client(SUPABASE_URL, key)
    # Try a lightweight call
    print("Client initialized. Attempting simple select (this might fail if table doesn't exist, but connection should work)...")
    # Just check if we can build the query, execute might fail auth or table
    # We'll try to fetch 0 rows from a likely existing table or just check health if possible.
    # Supabase doesn't have a simple 'ping' method exposed easily, so we try the upsert that was failing.
    # But let's try a simple select first.
    res = client.table("econ_indicators").select("*").limit(1).execute()
    print(f"SUCCESS: Supabase Query executed. Data: {res.data}")
except Exception as e:
    print(f"FAILURE: Supabase SDK failed: {e}")
