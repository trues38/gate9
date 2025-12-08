from utils.supabase_client import run_sql
import json

def check_schema():
    print("🔍 Checking Supabase Schema...")
    
    tables = ["global_news_all", "youtube_transcripts"]
    
    for table in tables:
        print(f"\n📋 Table: {table}")
        query = f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        """
        try:
            res = run_sql(query)
            print(f"   RAW RESPONSE: {res}") # Debug print
            if isinstance(res, list):
                for col in res:
                    # Handle potential key variations
                    c_name = col.get('column_name') or col.get('COLUMN_NAME')
                    d_type = col.get('data_type') or col.get('DATA_TYPE')
                    if c_name:
                        print(f"   - {c_name} ({d_type})")
                    else:
                        print(f"   ⚠️ Key not found in: {col}")
            else:
                print(f"   ⚠️ Unexpected response: {res}")
        except Exception as e:
            print(f"   ❌ Failed to fetch schema: {e}")

if __name__ == "__main__":
    check_schema()
