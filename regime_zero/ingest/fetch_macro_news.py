import feedparser
import pandas as pd
from datetime import datetime
import time
import os
import argparse
from dotenv import load_dotenv
from supabase import create_client
from ingest_utils import RegexCleaner, DeduplicationFilter, KeywordFilter

# Load Env
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Spec Definitions
SPECS = {
    "FED": {
        "keywords": ["fed", "fomc", "powell", "governor", "rate", "interest", "inflation", "policy", "monetary", "dot plot"],
        "min_length": 30,
        "sources": [
            {"name": "FRB_Press", "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
            {"name": "FRB_Speeches", "url": "https://www.federalreserve.gov/feeds/speeches.xml"},
            {"name": "FRB_BeigeBook", "url": "https://www.federalreserve.gov/feeds/beige_book.xml"},
            {"name": "Reuters_Fed", "url": "https://www.reuters.com/markets/us/federalreserve/rss"},
            {"name": "WSJ_Fed", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"}, 
        ]
    },
    "OIL": {
        "keywords": ["oil", "brent", "wti", "crude", "opec", "supply", "inventory", "production", "geopolitics", "energy"],
        "min_length": 25,
        "sources": [
            {"name": "Reuters_Energy", "url": "https://www.reuters.com/markets/commodities/rss"},
            {"name": "Oilprice.com", "url": "https://oilprice.com/rss/main"},
            {"name": "MarketWatch_Energy", "url": "https://feeds.marketwatch.com/marketwatch/energy/"},
        ]
    },
    "GOLD": {
        "keywords": ["gold", "xau", "safe haven", "bullion", "metal", "precious", "dollar", "yield"],
        "min_length": 25,
        "sources": [
            {"name": "Kitco_Gold", "url": "https://www.kitco.com/rss/gold.xml"},
            {"name": "Reuters_Metals", "url": "https://www.reuters.com/markets/metals/rss"},
            {"name": "FXStreet_Gold", "url": "https://www.fxstreet.com/rss"}, 
        ]
    }
}

def fetch_rss(source):
    print(f"   📡 Fetching {source['name']}...")
    try:
        feed = feedparser.parse(source['url'])
        articles = []
        for entry in feed.entries:
            # Date Parsing
            published = ""
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                published = dt.strftime("%Y-%m-%d %H:%M:%S")
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                published = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                published = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            articles.append({
                "title": entry.title,
                "url": entry.link,
                "published_at": published,
                "source": source['name'],
                "raw_data": {
                    "summary": entry.get('summary', ''),
                    "original_published": published
                }
            })
        return articles
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def process_category(category):
    spec = SPECS[category]
    print(f"\n🚀 Processing Category: {category}")
    
    # Initialize Filters
    cleaner = RegexCleaner()
    keyword_filter = KeywordFilter(spec['keywords'])
    
    new_articles = []
    
    for source in spec['sources']:
        raw_articles = fetch_rss(source)
        
        for a in raw_articles:
            title = cleaner.clean_title(a['title'])
            
            # 1. Length Check
            if len(title) < spec['min_length']:
                continue
                
            # 2. Regex Noise Check
            if not cleaner.is_clean(title):
                continue
                
            # 3. Keyword Whitelist Check
            if not keyword_filter.passes(title):
                continue
                
            # 4. Prepare for DB
            a['title'] = title
            a['country'] = 'US' # Default for macro sources
            a['raw_data']['category'] = category
            
            new_articles.append(a)
            
    print(f"   ✅ Found {len(new_articles)} valid articles.")
    
    if new_articles:
        try:
            # Upsert to news_raw
            supabase.table("news_raw").upsert(new_articles, on_conflict="url").execute()
            print(f"   💾 Saved {len(new_articles)} to news_raw")
        except Exception as e:
            print(f"   ❌ DB Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, choices=["FED", "OIL", "GOLD", "ALL"], default="ALL")
    args = parser.parse_args()
    
    if args.category == "ALL":
        for cat in ["FED", "OIL", "GOLD"]:
            process_category(cat)
    else:
        process_category(args.category)
