import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_rate():
    print("📊 Analyzing Ingestion Rate...")
    
    # 1. Total Count
    # Supabase-py doesn't have a direct count() without fetching, but we can select head=True
    res_total = supabase.table("ingest_news").select("id", count="exact").execute()
    total_count = res_total.count
    print(f"   Total Items: {total_count}")
    
    # 2. Last 24 Hours
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    res_daily = supabase.table("ingest_news").select("id", count="exact").gt("created_at", yesterday).execute()
    daily_count = res_daily.count
    print(f"   Last 24 Hours: {daily_count}")
    
    # 3. Projection
    monthly_est = daily_count * 30
    print(f"   30-Day Estimate: {monthly_est}")
    
    # 4. Average Size (Optional, rough guess)
    # Assuming 1KB per row (text + metadata)
    size_mb = (monthly_est * 1) / 1024
    print(f"   Est. Monthly Size: {size_mb:.2f} MB")

if __name__ == "__main__":
    check_rate()
