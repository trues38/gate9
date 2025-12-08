import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client
from generate_strategies import process_pattern

load_dotenv(override=True)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

async def main():
    print("🔄 Retrying P-014...")
    response = supabase.table("macro_patterns").select("*").eq("pattern_id", "P-014").execute()
    if not response.data:
        print("❌ P-014 not found in DB")
        return
    
    pattern = response.data[0]
    await process_pattern(pattern)
    print("✨ P-014 Retry Complete")

if __name__ == "__main__":
    asyncio.run(main())
