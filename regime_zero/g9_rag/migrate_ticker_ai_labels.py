import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.supabase_client import run_sql

def migrate_ticker_ai_labels():
    print("🚀 Migrating 'ticker_ai_labels' table...")
    
    sql = """
    ALTER TABLE ticker_ai_labels ADD COLUMN IF NOT EXISTS candidate_tickers TEXT[];
    ALTER TABLE ticker_ai_labels ADD COLUMN IF NOT EXISTS reasoning TEXT;
    
    SELECT 1;
    """
    
    try:
        res = run_sql(sql)
        print("✅ Table 'ticker_ai_labels' migrated.")
    except Exception as e:
        print(f"❌ Failed to migrate table: {e}")

if __name__ == "__main__":
    migrate_ticker_ai_labels()
