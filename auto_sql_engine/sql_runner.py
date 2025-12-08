from utils.supabase_client import run_sql

def execute_sql(sql):
    try:
        # Wrap in json_agg to ensure run_sql RPC returns full result set
        wrapped_sql = f"SELECT json_agg(t) FROM ({sql}) t;"
        return run_sql(wrapped_sql)
    except Exception as e:
        return {"error": str(e), "sql": sql}
