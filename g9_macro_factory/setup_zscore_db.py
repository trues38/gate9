import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
    sys.exit(1)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_client import run_sql

def setup_zscore_db():
    print("🛠️ Setting up Z-Score DB...")
    
    # Create zscore_daily table with hierarchical columns
    sql = """
    CREATE TABLE IF NOT EXISTS zscore_daily (
        date DATE PRIMARY KEY,
        count INT,
        z_score FLOAT, -- Legacy or Global
        z_year FLOAT,  -- (Month_Avg - Year_Avg) / Year_Std
        z_day_local FLOAT, -- (Day - Month_Avg) / Month_Std
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
    );
    """
    run_sql(sql)
    print("✅ zscore_daily table ready.")

if __name__ == "__main__":
    setup_zscore_db()
