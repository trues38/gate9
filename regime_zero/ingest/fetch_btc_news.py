import feedparser
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import os
import urllib.parse
import re
import hashlib
import argparse

# Configuration
OUTPUT_DIR = "regime_zero/data/multi_asset_history"
OUTPUT_FILE = f"{OUTPUT_DIR}/btc_news_history.csv"

# Map Source Name to Domain for Google Query
SOURCE_DOMAINS = {
    "CoinDesk": "coindesk.com",
    "Cointelegraph": "cointelegraph.com",
    "Bitcoin.com": "news.bitcoin.com",
    "CryptoNews": "cryptonews.com",
    "CryptoPolitan": "cryptopolitan.com"
}

class RegexCleaner:
    """Filters out noise and spam using Regex."""
    def __init__(self):
        # Patterns to exclude
        self.exclude_patterns = [
            r"(?i)sponsored",
            r"(?i)press release",
            r"(?i)promoted",
            r"(?i)gamble",
            r"(?i)casino",
            r"(?i)sex",
            r"(?i)porn",
            r"(?i)dating",
            r"(?i)18\+",
            r"(?i)subscribe",
            r"(?i)newsletter"
        ]
        self.compiled_patterns = [re.compile(p) for p in self.exclude_patterns]

    def is_clean(self, text):
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return False
        return True
    
    def clean_title(self, title):
        # Remove common suffixes like " - CoinDesk"
        if " - " in title:
            title = title.rsplit(" - ", 1)[0]
        if " | " in title:
            title = title.rsplit(" | ", 1)[0]
        return title.strip()

class DeduplicationFilter:
    """
    Simulates a Bloom Filter using a Set of Hashes.
    For 1M records, a set of 32-byte hashes is ~32MB RAM, which is fine.
    """
    def __init__(self):
        self.seen_hashes = set()
    
    def _get_hash(self, text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def add(self, text):
        h = self._get_hash(text)
        self.seen_hashes.add(h)
        
    def exists(self, text):
        h = self._get_hash(text)
        return h in self.seen_hashes
    
    def load_existing(self, filepath):
        if os.path.exists(filepath):
            print(f"🔄 Loading existing data from {filepath} for deduplication...")
            try:
                df = pd.read_csv(filepath)
                # Assume duplicates are based on Title + Date (since links vary)
                for _, row in df.iterrows():
                    unique_str = f"{row['title']}|{row['published']}"
                    self.add(unique_str)
                print(f"✅ Loaded {len(self.seen_hashes)} unique items into filter.")
            except Exception as e:
                print(f"⚠️ Failed to load existing data: {e}")

def fetch_google_news_rss(domain, start_date, end_date, cleaner, dedup_filter):
    """
    Fetches Google News RSS for a specific site and date range.
    """
    query = f"site:{domain} bitcoin after:{start_date} before:{end_date}"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    # print(f"   🔎 Query: {query}")
    
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries:
            # Parse Date
            try:
                dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                published = dt.strftime("%Y-%m-%d")
            except:
                published = ""

            # Clean Title
            raw_title = entry.title
            clean_title = cleaner.clean_title(raw_title)
            
            # 1. Regex Filter
            if not cleaner.is_clean(clean_title):
                continue
                
            # 2. Deduplication Filter (Bloom/Hash)
            # Use Title + Date as unique key
            unique_key = f"{clean_title}|{published}"
            
            if dedup_filter.exists(unique_key):
                continue
            
            # Add to Filter
            dedup_filter.add(unique_key)

            articles.append({
                "title": clean_title,
                "link": entry.link,
                "published": published,
                "source": domain
            })
        
        if articles:
            print(f"   ✅ {domain}: Found {len(articles)} new articles.")
        return articles
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def crawl_history_by_month(start_year=2020, end_year=2025):
    print(f"🚀 Starting Historical Crawl ({start_year}-{end_year}) with Refinement...")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Initialize Filters
    cleaner = RegexCleaner()
    dedup_filter = DeduplicationFilter()
    
    # Load existing data to populate Bloom/Hash Filter
    dedup_filter.load_existing(OUTPUT_FILE)
    
    all_articles = []
    
    # Generate Monthly Intervals
    current_date = datetime(start_year, 1, 1)
    end_date_limit = datetime(end_year, 12, 31)
    
    while current_date < end_date_limit:
        next_month = current_date + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        s_date = current_date.strftime("%Y-%m-%d")
        e_date = next_month.strftime("%Y-%m-%d")
        
        print(f"📅 Processing: {s_date} to {e_date}")
        
        month_articles = []
        for name, domain in SOURCE_DOMAINS.items():
            articles = fetch_google_news_rss(domain, s_date, e_date, cleaner, dedup_filter)
            for a in articles:
                a['source'] = name
            month_articles.extend(articles)
            month_articles.extend(articles)
            
            # Stealth Delay (3-7 seconds between domains)
            delay = random.uniform(3, 7)
            print(f"   zzz Sleeping {delay:.1f}s...")
            time.sleep(delay)
            
        # Incremental Save (to avoid memory issues and data loss)
        if month_articles:
            df = pd.DataFrame(month_articles)
            # Append mode
            header = not os.path.exists(OUTPUT_FILE)
            df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False)
            print(f"   💾 Saved {len(month_articles)} items to CSV.")
        
        # Stealth Delay between Months (5-10 seconds)
        month_delay = random.uniform(5, 10)
        print(f"🌙 Month Complete. Sleeping {month_delay:.1f}s before next month...")
        time.sleep(month_delay)
            
        current_date = next_month

    print(f"\n✅ Crawl Complete. Total Unique Items in Filter: {len(dedup_filter.seen_hashes)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl Historical Bitcoin News via Google News RSS")
    parser.add_argument("--start", type=int, default=2025, help="Start Year (e.g. 2020)")
    parser.add_argument("--end", type=int, default=2025, help="End Year (e.g. 2025)")
    parser.add_argument("--output", type=str, default="btc_news_history.csv", help="Output filename")
    
    args = parser.parse_args()
    
    # Update Global OUTPUT_FILE based on arg
    OUTPUT_FILE = f"{OUTPUT_DIR}/{args.output}"
    
    crawl_history_by_month(start_year=args.start, end_year=args.end)
