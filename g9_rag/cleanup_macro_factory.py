import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.supabase_client import run_sql

def cleanup_db():
    print("🧹 Cleaning up G9 Macro-Factory Tables...")
    
    sql = """
    DROP TABLE IF EXISTS backtest_results;
    DROP TABLE IF EXISTS anomaly_events;
    DROP TABLE IF EXISTS zscore_daily;
    
    SELECT 1;
    """
    
    try:
        res = run_sql(sql)
        print("✅ Tables dropped successfully.")
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")

if __name__ == "__main__":
    cleanup_db()
