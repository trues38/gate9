import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import os
import argparse

# Configuration
OUTPUT_FILE = "regime_zero/data/multi_asset_history/oil_news_archive.csv"
BASE_URL = "https://oilprice.com/Latest-Energy-News/World-News"

def fetch_oil_archive(start_page=1, end_page=50):
    print(f"🚀 Starting OIL Archive Scrape (Pages {start_page}-{end_page})...")
    
    all_articles = []
    
    for page in range(start_page, end_page + 1):
        if page == 1:
            url = f"{BASE_URL}/"
        else:
            url = f"{BASE_URL}/Page-{page}.html"
            
        print(f"   🛢️ Scraping Page {page}: {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"   ❌ Failed to fetch page {page}: Status {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"DEBUG: {soup.prettify()[:1000]}")
            
            # Selector: Oilprice usually has div.categoryArticle
            # Or look for div.categoryArticle__content
            
            articles = soup.select("div.categoryArticle__content")
            if not articles:
                # Fallback to broader selector
                articles = soup.select("div.categoryArticle")
            
            count = 0
            for item in articles:
                try:
                    # Title & Link
                    link_tag = item.select_one("a")
                    if not link_tag: continue
                    
                    title = link_tag.get_text(strip=True)
                    link = link_tag['href']
                    
                    # Date & Author
                    # usually in p.categoryArticle__meta
                    meta = item.select_one("p.categoryArticle__meta")
                    published = ""
                    if meta:
                        # Text: "Dec 02, 2025 at 10:04 | Charles Kennedy"
                        meta_text = meta.get_text(strip=True)
                        
                        # Split by "|" to separate author
                        date_part = meta_text.split("|")[0].strip()
                        
                        # Split by "at" to remove time
                        if "at" in date_part:
                            date_part = date_part.split("at")[0].strip()
                            
                        try:
                            # Parse "Dec 02, 2025"
                            dt = datetime.strptime(date_part, "%b %d, %Y")
                            published = dt.strftime("%Y-%m-%d")
                        except:
                            published = date_part # Keep original if fail
                    
                    if not published:
                        # Fallback: Use today if page 1, else unknown
                        published = "Unknown"
                        if count == 0:
                            print(f"DEBUG ITEM: {item.prettify()}")

                    if title and link:
                        all_articles.append({
                            "title": title,
                            "link": link,
                            "published": published,
                            "source": "Oilprice_Archive"
                        })
                        count += 1
                except Exception as e:
                    continue
            
            print(f"   ✅ Found {count} articles.")
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Save
    if all_articles:
        df = pd.DataFrame(all_articles)
        mode = 'a' if os.path.exists(OUTPUT_FILE) else 'w'
        header = not os.path.exists(OUTPUT_FILE)
        df.to_csv(OUTPUT_FILE, mode=mode, header=header, index=False)
        print(f"💾 Saved {len(all_articles)} articles to {OUTPUT_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=50, help="Number of pages")
    args = parser.parse_args()
    
    fetch_oil_archive(end_page=args.pages)
