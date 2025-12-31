import os
import sys
# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_client import run_sql

def create_table_via_rpc():
    print("🚀 Creating 'antigravity_reports' table via RPC...")
    
    sql = """
    DROP TABLE IF EXISTS antigravity_reports;
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
        embedding vector(1536),
        quality_score INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
    );
    
    CREATE INDEX IF NOT EXISTS antigravity_reports_embedding_idx ON antigravity_reports USING hnsw (embedding vector_cosine_ops);
    
    SELECT 1;
    """
    
    try:
        # run_sql expects a query string
        # Note: The run_sql implementation in utils/supabase_client.py sends {"query": query} to rpc/run_sql
        # This assumes the 'run_sql' function exists in Postgres.
        res = run_sql(sql)
        print("✅ Table created successfully via RPC.")
        print(f"Response: {res}")
    except Exception as e:
        print(f"❌ Failed to create table via RPC: {e}")
        print("   (The 'run_sql' RPC function might not exist. If so, please run the SQL manually in Supabase Dashboard.)")

if __name__ == "__main__":
    create_table_via_rpc()
