import feedparser
from datetime import datetime
import json

# "New Era" Sources: Tech, Crypto, Future Trends
NEW_ERA_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Wired_Business": "https://www.wired.com/feed/category/business/latest/rss",
    "Wired_Science": "https://www.wired.com/feed/category/science/latest/rss"
}

def fetch_new_era_context(limit_per_source=3):
    """
    Fetches headlines from 'New Era' sources to capture modern context 
    (Crypto, AI, Tech, Future Science) that might not be in historical data.
    """
    print("🌐 [New Era] Scanning the Horizon (Tech, Crypto, Future)...")
    
    context_data = []
    
    for source, url in NEW_ERA_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:limit_per_source]
            
            for entry in entries:
                context_data.append({
                    "source": source,
                    "title": entry.title,
                    "summary": entry.get("summary", "")[:200] + "...", # Truncate summary
                    "published": entry.get("published", datetime.now().strftime("%Y-%m-%d"))
                })
        except Exception as e:
            print(f"⚠️ [New Era] Failed to fetch {source}: {e}")

    # Format as a string for the LLM
    context_str = "## 🚀 New Era Signals (Real-time/Future Context)\n"
    if not context_data:
        context_str += "No new era signals detected (Feed Error).\n"
    else:
        for item in context_data:
            context_str += f"- [{item['source']}] {item['title']} ({item['published']})\n"
            
    return context_str

if __name__ == "__main__":
    # Test run
    print(fetch_new_era_context())
