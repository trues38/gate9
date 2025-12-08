import os
import sys
import time
import feedparser
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# --- CONFIGURATION ---
TARGET_CROPS = {
    "onion": ["양파", "양파 가격", "양파 작황"],
    "cabbage": ["배추", "배추 가격", "김장 배추", "고랭지 배추"],
    "radish": ["무", "무 가격", "김장 무"],
    "garlic": ["마늘", "마늘 가격", "난지형 마늘"],
    "pepper": ["건고추", "고춧가루", "홍고추"],
    "potato": ["감자", "수미 감자", "감자 가격"]
}

def clean_html_summary(html_content):
    """Removes HTML tags from summary."""
    if not html_content: return ""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")
    return re.sub(r'\s+', ' ', text).strip()

def fetch_crop_news():
    print(f"🚜 [Agri-News] Starting Ingestion... [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    all_articles = []
    
    for crop_code, keywords in TARGET_CROPS.items():
        print(f"   🔍 Searching for {crop_code} ({keywords[0]})...")
        
        for keyword in keywords:
            # Google News RSS (Korean)
            url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
            
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    # Parse Date
                    published = entry.get('published', str(datetime.now()))
                    try:
                        dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                        published_iso = dt.strftime("%Y-%m-%d") # Store as Date for Agri DB
                    except:
                        published_iso = datetime.now().strftime("%Y-%m-%d")

                    all_articles.append({
                        "date": published_iso,
                        "crop": crop_code,
                        "title": entry.title,
                        "url": entry.link,
                        "summary": clean_html_summary(entry.get('summary', '')),
                        "extracted_keywords": [keyword], # Initial keyword
                        "region": "KR", # Default
                        "source": "GoogleNews"
                    })
                    
            except Exception as e:
                print(f"      ❌ Error fetching {keyword}: {e}")
                
            time.sleep(0.5) # Be polite

    # Deduplicate by URL in memory before inserting
    unique_articles = {a['url']: a for a in all_articles}.values()
    
    print(f"   📥 Found {len(unique_articles)} unique articles.")
    
    # --- SAVE TO LOCAL RAW FILE (Data Lake) ---
    # Even if DB fails, we have the data.
    import json
    raw_dir = "data/agri_raw"
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{raw_dir}/news_{today_str}.jsonl"
    
    with open(filename, "a", encoding="utf-8") as f:
        for article in unique_articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
    print(f"   💾 Saved raw data to {filename}")

    # --- SAVE TO SUPABASE ---
    if unique_articles:
        batch_size = 50
        articles_list = list(unique_articles)
        
        for i in range(0, len(articles_list), batch_size):
            batch = articles_list[i:i+batch_size]
            try:
                # Use ignore_duplicates=True to avoid crashing on existing URLs
                supabase.table("crop_news_headlines").upsert(batch, on_conflict='url', ignore_duplicates=True).execute()
                print(f"      ✅ Saved batch {i//batch_size + 1} to DB")
            except Exception as e:
                print(f"      ⚠️ DB Save Error (Skipping): {e}")
                
    print("   ✨ Agri-News Ingestion Complete.")

if __name__ == "__main__":
    fetch_crop_news()
