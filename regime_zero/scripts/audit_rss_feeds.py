import feedparser
import time
from datetime import datetime
import sys

# Define the feeds to audit
FEEDS = {
    "Reuters Business": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", # Alternative
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC Business": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "AP News Business": "https://apnews.com/business.rss",
    "WSJ Markets": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "Yonhap Economy (KR)": "https://www.yna.co.kr/rss/economy.xml",
    "Edaily Economy (KR)": "http://rss.edaily.co.kr/economy_news.xml",
    "ChosunBiz (KR)": "https://biz.chosun.com/site/data/rss/rss.xml"
}

def audit_feeds():
    print(f"🔍 RSS Feed Audit Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []

    for name, url in FEEDS.items():
        print(f"Testing {name}...", end=" ")
        try:
            start_time = time.time()
            # Add User-Agent to avoid 403/Connection Reset
            feed = feedparser.parse(url, agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            elapsed = time.time() - start_time
            
            if feed.bozo:
                status = "PARTIAL (XML Error)"
                details = f"Bozo Exception: {feed.bozo_exception}"
            elif not feed.entries:
                status = "FAIL (Empty)"
                details = "No entries found"
            else:
                status = "SUCCESS"
                latest_entry = feed.entries[0]
                pub_date = latest_entry.get('published', 'No Date')
                details = f"{len(feed.entries)} items. Latest: {pub_date}"
                
            print(f"[{status}] ({elapsed:.2f}s)")
            results.append({
                "name": name,
                "url": url,
                "status": status,
                "details": details,
                "latency": f"{elapsed:.2f}s"
            })
            
        except Exception as e:
            print(f"[FAIL] Error: {e}")
            results.append({
                "name": name,
                "url": url,
                "status": "FAIL (Exception)",
                "details": str(e),
                "latency": "N/A"
            })

    print("\n" + "="*60)
    print("📊 Audit Summary")
    print("="*60)
    print(f"{'Source':<20} | {'Status':<20} | {'Details'}")
    print("-" * 80)
    for r in results:
        print(f"{r['name']:<20} | {r['status']:<20} | {r['details']}")

if __name__ == "__main__":
    audit_feeds()
