import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

key = os.environ.get("SUPABASE_KEY")

if not key:
    # Try alternate name
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not key:
    print("❌ No Key found in .env")
else:
    print("\n" + "="*40)
    print("🔑 KEY IN YOUR .ENV FILE")
    print("="*40)
    print(f"Algorithm Header (Start): {key[:15]}...")
    print(f"Signature (End 10 chars): ...{key[-10:]}")
    print("="*40)
    print("👉 Please compare these LAST 10 characters with the website.")
    print("If they are different, YOU MUST COPY the one from the website.")
