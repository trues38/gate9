import os
import sys
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g9_macro_factory.config import get_supabase_client
from utils.supabase_client import run_sql

def setup_db():
    print("🚀 Setting up Backtest Engine Database Tables...")
    
    sql = """
    -- 1. Price Daily Table
    CREATE TABLE IF NOT EXISTS price_daily (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        date DATE NOT NULL,
        ticker TEXT NOT NULL,
        close DOUBLE PRECISION NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        UNIQUE(date, ticker)
    );
    
    -- 2. Strategy Memory Table (Success Store)
    CREATE TABLE IF NOT EXISTS strategy_memory (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        date DATE NOT NULL,
        ticker TEXT NOT NULL,
        action TEXT NOT NULL, -- BUY / SELL
        reason TEXT,
        confidence DOUBLE PRECISION,
        entry_price DOUBLE PRECISION,
        exit_price DOUBLE PRECISION,
        return_pct DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    
    SELECT 1;
    """
    
    try:
        res = run_sql(sql)
        print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")

if __name__ == "__main__":
    setup_db()
