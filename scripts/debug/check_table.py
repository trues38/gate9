from utils.supabase_client import run_sql
import json

def check_table():
    q = "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'global_news_all';"
    res = run_sql(q)
    print(f"Check Result: {json.dumps(res, indent=2)}")
    
    q2 = "SELECT count(*) FROM global_news_all;"
    try:
        res2 = run_sql(q2)
        print(f"Row Count: {json.dumps(res2, indent=2)}")
    except Exception as e:
        print(f"Table access failed: {e}")

if __name__ == "__main__":
    check_table()
