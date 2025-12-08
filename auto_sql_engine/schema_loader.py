from utils.supabase_client import run_sql

def load_schema():
    q = """
    SELECT json_agg(t) FROM (
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'global_news_all'
        ORDER BY ordinal_position
    ) t;
    """
    return run_sql(q)
