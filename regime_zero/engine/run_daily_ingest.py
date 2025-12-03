import os
import sys
import time
import feedparser
import yfinance as yf
import pandas as pd
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# --- CONFIGURATION ---
ASSETS = {
    "DX-Y.NYB": "Dollar Index",
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "^TNX": "US 10Y Yield",
    "^VIX": "VIX Volatility Index",
    "SPY": "S&P 500",
    "BTC-USD": "Bitcoin"
}

NEWS_COUNTRIES = ["US", "KR", "JP", "CN"]
NEWS_TOPICS = ["BUSINESS", "WORLD"]

# --- HELPER FUNCTIONS ---

def clean_title(title):
    """Removes common noise from titles."""
    title = re.sub(r'\s+[-|]\s+.*$', '', title)
    return title.strip()

def clean_html_summary(html_content):
    """Removes HTML tags from summary."""
    if not html_content: return ""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")
    return re.sub(r'\s+', ' ', text).strip()

# --- MODULE 1: MARKET DATA INGEST ---

def fetch_market_data():
    print("\n📊 [1/2] Fetching Market Data (yfinance)...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d") # Just fetch recent to be safe
    
    total_saved = 0
    
    for ticker, name in ASSETS.items():
        print(f"   📥 {name} ({ticker})...", end=" ")
        try:
            df = yf.download(ticker, start=start_date, progress=False)
            
            if df.empty:
                print("❌ No Data")
                continue
                
            # Reset index and flatten
            df = df.reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Prepare DB Rows
            db_rows = []
            for _, row in df.iterrows():
                try:
                    # Handle Series vs Scalar
                    open_val = float(row['Open'].iloc[0]) if isinstance(row['Open'], pd.Series) else float(row['Open'])
                    close_val = float(row['Close'].iloc[0]) if isinstance(row['Close'], pd.Series) else float(row['Close'])
                    high_val = float(row['High'].iloc[0]) if isinstance(row['High'], pd.Series) else float(row['High'])
                    low_val = float(row['Low'].iloc[0]) if isinstance(row['Low'], pd.Series) else float(row['Low'])
                    vol_val = int(row['Volume'].iloc[0]) if isinstance(row['Volume'], pd.Series) else int(row['Volume'])
                    
                    if pd.isna(open_val) or pd.isna(close_val): continue

                    db_rows.append({
                        "date": row['Date'].strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "open": open_val,
                        "close": close_val,
                        "high": high_val,
                        "low": low_val,
                        "volume": vol_val
                    })
                except Exception as e:
                    continue

            if db_rows:
                supabase.table("ingest_prices").upsert(db_rows).execute()
                print(f"✅ Saved {len(db_rows)} rows")
                total_saved += len(db_rows)
            else:
                print("⚠️ No valid rows")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
    print(f"   ✨ Market Data Complete. ({total_saved} updates)")

# --- MODULE 2: NEWS INGEST ---

# --- MODULE 2: NEWS INGEST ---

# Direct RSS Feeds (Verified Working)
DIRECT_FEEDS = {
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "WSJ": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "Nikkei": "https://asia.nikkei.com/rss/feed/nar",
    "Yonhap": "https://www.yna.co.kr/rss/economy.xml"
}

def fetch_direct_feeds():
    """Fetches news from verified direct RSS feeds."""
    print("\n📡 [Direct] Fetching Verified RSS Feeds...")
    articles = []
    
    for source, url in DIRECT_FEEDS.items():
        print(f"   Trying {source}...", end=" ")
        try:
            # Add User-Agent to avoid 403
            feed = feedparser.parse(url, agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            if not feed.entries:
                print("❌ Empty")
                continue
                
            print(f"✅ {len(feed.entries)} items")
            
            for entry in feed.entries:
                # Determine Country based on source
                country = "US"
                if source in ["Nikkei", "Yonhap"]: country = "KR" # Nikkei is Asia but often relevant to KR/JP. Let's map Nikkei to JP/Asia? User has JP.
                if source == "Nikkei": country = "JP"
                if source == "Yonhap": country = "KR"
                
                published = entry.get('published', str(datetime.now()))
                try:
                    # Try common formats
                    dt = datetime.now() # Fallback
                    # (Parsing logic can be complex, relying on string for now or simple parse)
                    # feedparser usually returns struct_time
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    published_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    published_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                articles.append({
                    "country": country,
                    "title": entry.title,
                    "clean_title": clean_title(entry.title),
                    "summary": clean_html_summary(entry.get('summary', '')),
                    "url": entry.link,
                    "published_at": published_iso,
                    "ticker": "",
                    "source": source,
                    "category": "ECONOMY", # Default to ECONOMY for these business feeds
                    "is_refined": False # Needs refinement
                })
        except Exception as e:
            print(f"❌ Error: {e}")
            
    return articles

def fetch_rss_feed(country_code, topic="BUSINESS"):
    base_url = "https://news.google.com/rss"
    
    # Config
    configs = {
        "US": {"ceid": "US:en", "gl": "US", "hl": "en-US"},
        "KR": {"ceid": "KR:ko", "gl": "KR", "hl": "ko"},
        "JP": {"ceid": "JP:ja", "gl": "JP", "hl": "ja"},
        "CN": {"ceid": "HK:zh-Hant", "gl": "HK", "hl": "zh-Hant"}, # Use HK for CN proxy
    }
    
    c = configs.get(country_code, configs["US"])
    url = f"{base_url}/headlines/section/topic/{topic}?ceid={c['ceid']}&gl={c['gl']}&hl={c['hl']}"
    
    try:
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries:
            published = entry.published if 'published' in entry else str(datetime.now())
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                published_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                published_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            articles.append({
                "country": country_code,
                "title": entry.title,
                "clean_title": clean_title(entry.title),
                "summary": clean_html_summary(entry.summary) if 'summary' in entry else "",
                "url": entry.link,
                "published_at": published_iso,
                "ticker": "",
                "source": "GoogleNews",
                "category": topic.lower(),
                "is_refined": False
            })
        return articles
    except Exception as e:
        print(f"   ❌ RSS Error {country_code}: {e}")
        return []

def fetch_news():
    print("\n📰 [2/2] Fetching Global News (RSS)...")
    
    all_articles = []
    
    # 1. Fetch Direct Feeds (High Quality)
    direct_articles = fetch_direct_feeds()
    all_articles.extend(direct_articles)

    # 2. Fetch Google News (Fallback/Broad)
    print("\n📡 [Google] Fetching Broad News...")
    for country in NEWS_COUNTRIES:
        for topic in NEWS_TOPICS:
            print(f"   📡 Fetching {country} / {topic}...", end=" ")
            articles = fetch_rss_feed(country, topic)
            print(f"✅ {len(articles)} articles")
            all_articles.extend(articles)
            time.sleep(0.5)
            
    if all_articles:
        print(f"   💾 Saving {len(all_articles)} articles to Supabase...")
        # Batch upsert
        batch_size = 50
        for i in range(0, len(all_articles), batch_size):
            batch = all_articles[i:i+batch_size]
            try:
                supabase.table("ingest_news").upsert(batch).execute()
            except Exception as e:
                if "duplicate key" not in str(e):
                    print(f"      ⚠️ Save Error: {e}")
        print("   ✨ News Ingest Complete.")
    else:
        print("   ⚠️ No news found.")

# --- MAIN ---

def run_daily_ingest():
    print(f"🚀 REGIME ZERO DAILY INGEST [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("="*60)
    
    fetch_market_data()
    fetch_news()
    
    print("\n🎉 INGEST COMPLETE! System is ready for analysis.")

if __name__ == "__main__":
    run_daily_ingest()
