from utils.supabase_client import run_sql
import json

def check_columns():
    q = """
    SELECT json_agg(t) FROM (
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'global_news_all'
        ORDER BY ordinal_position
    ) t;
    """
    res = run_sql(q)
    print(f"Columns: {json.dumps(res, indent=2)}")

if __name__ == "__main__":
    check_columns()
