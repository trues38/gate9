import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import os
import argparse

# Configuration
OUTPUT_FILE = "regime_zero/data/multi_asset_history/gold_news_archive.csv"
BASE_URL = "https://www.kitco.com/news/category/commodities"

def fetch_gold_archive(start_page=1, end_page=50):
    print(f"🚀 Starting GOLD Archive Scrape (Pages {start_page}-{end_page})...")
    
    all_articles = []
    
    for page in range(start_page, end_page + 1):
        url = f"{BASE_URL}?page={page}"
        print(f"   🥇 Scraping Page {page}: {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.kitco.com/"
            }
            # Kitco might be slow, give it time
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                print(f"   ❌ Failed to fetch page {page}: Status {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"DEBUG: {soup.prettify()[:500]}")
            
            # Selector: Broad h3 search
            # Kitco headlines are almost always in h3
            items = soup.find_all("h3")
            
            count = 0
            for item in items:
                try:
                    # Title & Link
                    link_tag = item.find("a")
                    if not link_tag:
                        # Maybe the h3 itself is the link? No, usually inside.
                        # Check if h3 parent is a link
                        link_tag = item.find_parent("a")
                    
                    if not link_tag: continue
                    
                    title = item.get_text(strip=True)
                    link = link_tag['href']
                    if link.startswith("/"):
                        link = "https://www.kitco.com" + link
                            
                    # Date
                    # Try to find a time/date element near the h3
                    # Go up to parent container
                    published = ""
                    parent = item.find_parent("div")
                    if parent:
                        date_tag = parent.select_one("time") or parent.select_one(".date")
                        if date_tag:
                            date_text = date_tag.get_text(strip=True)
                            try:
                                # Clean "Nov 28, 2025 - 5:30 PM" -> "Nov 28, 2025"
                                clean_date = date_text.split("-")[0].strip()
                                dt = datetime.strptime(clean_date, "%b %d, %Y")
                                published = dt.strftime("%Y-%m-%d")
                            except:
                                # Handle "25 minutes ago", "2 hours ago"
                                if "ago" in date_text.lower():
                                    published = datetime.now().strftime("%Y-%m-%d")
                                else:
                                    published = date_text

                    if not published:
                         published = "Unknown"

                    if title and link and len(title) > 10:
                        all_articles.append({
                            "title": title,
                            "link": link,
                            "published": published,
                            "source": "Kitco_Archive"
                        })
                        count += 1
                except Exception as e:
                    continue
            
            print(f"   ✅ Found {count} articles.")
            time.sleep(random.uniform(2, 4)) # Slower for Kitco
            
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
    
    fetch_gold_archive(end_page=args.pages)
