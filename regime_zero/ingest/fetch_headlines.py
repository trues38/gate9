import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def get_daily_headlines(target_date, limit=50, ticker=None):
    """
    Fetch headlines for a specific date from ingest_news.
    Prioritizes high signal_score if available.
    If ticker is provided, filters for that ticker (or related keywords).
    """
    print(f"📰 [Regime Zero] Fetching Headlines for {target_date} (Ticker: {ticker})...")
    
    try:
        # Define date range (full day)
        start_dt = f"{target_date} 00:00:00"
        end_dt = f"{target_date} 23:59:59"
        
        # Query Supabase
        query = supabase.table("ingest_news")\
            .select("title, summary, source, signal_score, published_at")\
            .gte("published_at", start_dt)\
            .lte("published_at", end_dt)\
            .order("published_at", desc=True)
            
        if ticker:
            # Simple keyword filter for now. 
            # In a real system, we'd use the 'tickers' array column if it exists and is populated.
            # For BTC, we check for 'Bitcoin', 'BTC', 'Crypto'.
            if ticker in ["BTC", "BITCOIN"]:
                query = query.or_("title.ilike.%Bitcoin%,title.ilike.%BTC%,title.ilike.%Crypto%,summary.ilike.%Bitcoin%")
            else:
                query = query.or_(f"title.ilike.%{ticker}%,summary.ilike.%{ticker}%")
        
        response = query.limit(limit).execute()
            
        headlines = []
        if response.data:
            for row in response.data:
                # Use summary if available and good quality, else title
                text = row.get('title', '')
                if row.get('summary'):
                    text += f": {row.get('summary')}"
                headlines.append(text)
        
        # Fallback: Unified History CSV
        if not headlines:
            print(f"⚠️ Supabase empty. Checking Unified History CSV...")
            csv_path = "regime_zero/data/multi_asset_history/unified_history.csv"
            if os.path.exists(csv_path):
                import pandas as pd
                try:
                    df = pd.read_csv(csv_path)
                    # Filter by date
                    # df['date'] is YYYY-MM-DD
                    day_news = df[df['date'] == target_date]
                    
                    if ticker:
                        # Filter by ticker/asset class
                        if ticker in ["BTC", "BITCOIN"]:
                            # Get BTC class + keyword match
                            mask = (day_news['asset_class'] == 'BTC') | \
                                   (day_news['title'].str.contains("Bitcoin|BTC|Crypto", case=False, na=False))
                            day_news = day_news[mask]
                        else:
                            # Generic keyword search
                            day_news = day_news[day_news['title'].str.contains(ticker, case=False, na=False)]
                    
                    # Take top N
                    for _, row in day_news.head(limit).iterrows():
                        headlines.append(f"{row['title']} (Source: {row['source']})")
                        
                    if headlines:
                        print(f"✅ Found {len(headlines)} headlines from CSV.")
                except Exception as e:
                    print(f"❌ CSV Fallback failed: {e}")

        if not headlines:
            print(f"⚠️ No headlines found for {target_date} (Ticker: {ticker})")
            
        return headlines

    except Exception as e:
        print(f"❌ Error fetching headlines: {e}")
        return []

if __name__ == "__main__":
    # Test
    test_date = datetime.now().strftime("%Y-%m-%d")
    # test_date = "2024-11-29"
    news = get_daily_headlines(test_date)
    print(f"Found {len(news)} headlines:")
    for n in news[:5]:
        print(f"- {n}")
