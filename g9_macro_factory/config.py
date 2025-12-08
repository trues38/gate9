import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

def get_supabase_client() -> Client:
    """Returns a configured Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Database Table Names
TABLE_NEWS = "global_news_all" # Using global_news_all as news_items
TABLE_PRICE_DAILY = "price_daily"
TABLE_STRATEGY_MEMORY = "strategy_memory"

# Configuration Parameters
BACKTEST_CONTEXT_LIMIT = 500
SUCCESS_THRESHOLD_PCT = 3.0
