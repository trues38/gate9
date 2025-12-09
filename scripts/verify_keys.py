import os
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

# Use the keys found in the debug output
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ MISSING CREDENTIALS even after correction.")
    exit(1)

print(f"Testing Key: {key[:5]}...{key[-5:]}")

try:
    supabase: Client = create_client(url, key)
    # Try a lightweight operation
    data = supabase.from_("admin_system_status").select("*").limit(1).execute()
    print("✅ CONNECTION SUCCESS: The OLD key is STILL ALIVE.")
    print("⚠️ WARNING: Rotation DID NOT WORK immediately. (The key in .env is still valid)")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    print("🎉 SUCCESS: The OLD key is DEAD. (Rotation Worked!)")
