import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.supabase_client import run_sql

def create_ticker_ai_labels_table():
    print("🚀 Creating 'ticker_ai_labels' table...")
    
    # We use a unique constraint on (company, ticker) to avoid duplicates as requested.
    # But we also want to track confidence.
    # If we encounter the same (company, ticker), we might want to update the confidence if it's higher?
    # Or just ignore? User said "Same company/ticker combo is not stored as duplicates".
    # I will make (company, ticker) unique.
    
    sql = """
    CREATE TABLE IF NOT EXISTS ticker_ai_labels (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company TEXT NOT NULL,
        ticker TEXT,
        confidence FLOAT4,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        UNIQUE(company, ticker)
    );
    
    SELECT 1;
    """
    
    try:
        res = run_sql(sql)
        print("✅ Table 'ticker_ai_labels' created (or exists).")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")

if __name__ == "__main__":
    create_ticker_ai_labels_table()
