import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_table():
    print("🚀 Creating 'antigravity_reports' table...")
    
    # SQL to create the table
    # Note: We use `rpc` or direct SQL execution if enabled. 
    # Since we don't have direct SQL access via client usually, we might rely on the user having run it or use a workaround.
    # However, previous interactions suggest we can't easily run DDL via the python client unless we have a specific function.
    # But wait, the user's previous `setup_db.py` (if it existed) might have hints.
    # Actually, standard Supabase-py client doesn't support DDL directly unless using `rpc` to a function that executes SQL.
    # I will assume the user might need to run this SQL in their Supabase dashboard OR I can try to use `postgres` connection if available.
    # BUT, for this environment, I will try to use the `mcp3_execute_sql` tool if available? 
    # Checking available tools... `mcp3_execute_sql` IS available from `supabase-mcp-server`.
    # I should use that tool instead of a python script for DDL if possible.
    # But I am in a python script context. 
    # I will write the SQL here for the user to see, and then I will use the `mcp3_execute_sql` tool in the NEXT step to actually apply it.
    
    sql = """
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS antigravity_reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        date DATE NOT NULL,
        headline TEXT,
        pattern_ids TEXT[],
        final_thesis TEXT,
        dominant_narrative TEXT,
        strategy_bias TEXT,
        confirmed_signals TEXT[],
        weak_points TEXT[],
        counter_scenario TEXT,
        next_iteration_checklist TEXT[],
        embedding_text TEXT,
        embedding vector(3072),
        quality_score INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
    );
    
    -- Create index for faster vector search
    CREATE INDEX IF NOT EXISTS antigravity_reports_embedding_idx ON antigravity_reports USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """
    print("📋 SQL to be executed:")
    print(sql)
    
    # For now, I'll just save this script as a reference or "migration" file.
    with open("create_antigravity_reports.sql", "w") as f:
        f.write(sql)
    print("✅ SQL saved to create_antigravity_reports.sql")

if __name__ == "__main__":
    create_table()
