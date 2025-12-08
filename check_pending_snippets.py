from utils.supabase_client import run_sql
import json

def check_pending_snippets():
    print("🔍 Checking PENDING rows for snippets...")
    
    # Fetch 5 PENDING rows
    sql = """
    SELECT id, title, summary, raw_text 
    FROM global_news_all 
    WHERE summary_status = 'PENDING' 
    LIMIT 5
    """
    
    try:
        res = run_sql(sql)
        if not res:
            print("❌ No PENDING rows found.")
        else:
            print(f"✅ Found {len(res)} PENDING rows.")
            for item in res:
                print(f"\n--- [ID: {item.get('id')}] ---")
                print(f"Title: {item.get('title')}")
                print(f"Current Summary (Snippet?): {item.get('summary')}")
                print(f"Raw Text: {item.get('raw_text')}")
                
    except Exception as e:
        print(f"❌ Query Failed: {e}")

if __name__ == "__main__":
    check_pending_snippets()
