import os
import base64
import json
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not key:
    print("❌ No Key found.")
    exit(1)

parts = key.split('.')
if len(parts) != 3:
    print("❌ Invalid JWT format.")
    exit(1)

header_b64 = parts[0]
# Add padding if needed
header_b64 += '=' * (-len(header_b64) % 4)

try:
    header_bytes = base64.urlsafe_b64decode(header_b64)
    header = json.loads(header_bytes)
    
    print("\n" + "="*40)
    print("🔑 KEY ANALYSIS REPORT")
    print("="*40)
    print(f"Key Suffix: ...{key[-10:]}")
    print(f"Algorithm:  {header.get('alg', 'UNKNOWN')}")
    print(f"Type:       {header.get('typ', 'UNKNOWN')}")
    print("="*40)
    
    if header.get('alg') == 'HS256':
        print("⚠️  DANGER: This is a LEGACY Key (HS256).")
        print("    If you rotated to ECC, this key should be invalid soon.")
    elif header.get('alg') == 'ES256':
        print("✅  SAFE: This is a NEW ECC Key (ES256).")
        print("    You have successfully updated your .env file!")
    else:
        print("❓  Unknown Algorithm.")

except Exception as e:
    print(f"❌ Decode Error: {e}")
