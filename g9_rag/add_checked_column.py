import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.supabase_client import run_sql

def add_checked_column():
    print("🚀 Adding 'ai_ticker_checked' column to global_news_all...")
    
    sql = """
    ALTER TABLE global_news_all ADD COLUMN IF NOT EXISTS ai_ticker_checked BOOLEAN DEFAULT FALSE;
    SELECT 1;
    """
    
    try:
        res = run_sql(sql)
        print("✅ Column 'ai_ticker_checked' added.")
    except Exception as e:
        print(f"❌ Failed to add column: {e}")

if __name__ == "__main__":
    add_checked_column()
