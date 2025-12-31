import feedparser
import json
import os
from datetime import datetime

TACTICAL_FEEDS = [
    "https://spielverlagerung.com/feed/",
    "https://themastermindsite.com/feed/",
    "https://totalfootballanalysis.com/feed/",
    "https://breakingthelines.com/feed/"
]

def ingest_tactical_feeds():
    """
    Ingests tactical analysis articles from various RSS feeds for RAG.
    """
    articles = []
    for url in TACTICAL_FEEDS:
        print(f"Ingesting feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            article = {
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary,
                "source": url,
                "ingested_at": datetime.now().isoformat()
            }
            articles.append(article)
    
    output_path = "soccer_data/raw_data/tactical_rag/latest_articles.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    
    print(f"Total articles ingested: {len(articles)}")

if __name__ == "__main__":
    # pip install feedparser
    ingest_tactical_feeds()
