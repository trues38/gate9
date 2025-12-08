import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client, TABLE_NEWS, BACKTEST_CONTEXT_LIMIT

def retrieve_context(target_date_str):
    """
    Retrieves news items published BEFORE the target_date.
    Returns a list of dicts.
    """
    supabase = get_supabase_client()
    
    # Target date is the "Backtest Execution Date".
    # We can only see news BEFORE this timestamp (start of day).
    # So published_at < target_date 00:00:00
    
    print(f"   📥 Loading news context before {target_date_str}...")
    
    # We assume target_date_str is YYYY-MM-DD
    # We filter published_at < target_date_str
    
    # We also want recent news, not ancient history.
    # Let's say last 7 days? Spec says "date 이전 뉴스만 로드(500개 제한)".
    # It doesn't specify a start window, but 500 limit implies recency or relevance.
    # We should order by published_at DESC to get the MOST RECENT news before the date.
    
    # Optimize: Fetch only last 7 days of news to prevent full table scan/sort
    # This significantly speeds up the query and reduces DB load.
    start_date = datetime.strptime(target_date_str, "%Y-%m-%d") - timedelta(days=7)
    start_date_str = start_date.strftime("%Y-%m-%d")
    
    res = supabase.table(TABLE_NEWS)\
        .select("id, published_at, title, summary, ticker")\
        .lt("published_at", target_date_str)\
        .gt("published_at", start_date_str)\
        .order("published_at", desc=True)\
        .limit(BACKTEST_CONTEXT_LIMIT)\
        .execute()
        
    news_items = res.data
    print(f"   ✅ Loaded {len(news_items)} news items.")
    return news_items
