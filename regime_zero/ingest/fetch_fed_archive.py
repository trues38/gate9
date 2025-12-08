import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import os
import argparse

# Configuration
OUTPUT_FILE = "regime_zero/data/multi_asset_history/fed_news_archive.csv"
BASE_URL = "https://www.federalreserve.gov/newsevents/pressreleases.htm"

def fetch_fed_archive(start_year=2006, end_year=2025):
    print(f"🚀 Starting FED Archive Scrape ({start_year}-{end_year})...")
    
    all_articles = []
    
    for year in range(end_year, start_year - 1, -1):
        # Determine URL pattern based on year
        # Recent years (2016+): {year}-press.htm
        # Older years (2006-2015): {year}all.htm
        if year >= 2016:
            url = f"{BASE_URL.replace('.htm', '')}/{year}-press.htm"
        else:
            url = f"{BASE_URL.replace('.htm', '')}/{year}all.htm"
            
        print(f"   📄 Scraping Year {year}: {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ Failed to fetch {year}: Status {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Selector Strategy:
            # Inspecting the chunks, it seems the structure is likely a list of links.
            # Let's try to find the main content area first.
            # Usually "div#article" or "div.col-xs-12"
            # Then look for "div.row" or "li"
            
            # Based on typical Fed site structure:
            # <div class="row"> ... <div class="col-xs-12 col-md-8"> ... <ul> ... <li>
            
            # Let's try a broad selection of links inside the main content
            # We look for links that look like press releases (/newsevents/pressreleases/...)
            
            links = soup.select("a[href^='/newsevents/pressreleases/']")
            
            count = 0
            for link_tag in links:
                href = link_tag['href']
                title = link_tag.get_text(strip=True)
                
                # Filter out navigation links (like "2024", "Archive", "RSS")
                if not title or len(title) < 10: # Titles are usually long
                    continue
                if "View Press Releases" in title:
                    continue
                
                # Date Extraction
                # Often the date is in a preceding element or inside the link text?
                # Or maybe in a <time> tag nearby.
                # Let's try to find a date in the previous sibling or parent.
                
                # Strategy: Look for the closest date-like string
                # For now, default to Jan 1st of that year if not found, 
                # but let's try to find it.
                # In many Fed pages, it's: <div class="row"><div class="col-xs-3 date">...</div><div class="col-xs-9">...link...</div></div>
                
                published = f"{year}-01-01" # Fallback
                
                # Try finding a date container
                # Go up to parent (li or div)
                parent = link_tag.find_parent("div", class_="row") or link_tag.find_parent("li")
                if parent:
                    date_el = parent.select_one("time") or parent.select_one(".date") or parent.select_one("span")
                    if date_el:
                        date_text = date_el.get_text(strip=True)
                        try:
                            # Try parsing "January 1, 2025" or "1/1/2025"
                            # Fed usually uses "Month DD, YYYY"
                            dt = datetime.strptime(date_text, "%B %d, %Y")
                            published = dt.strftime("%Y-%m-%d")
                        except:
                            # Try extracting date from text if mixed
                            pass

                full_link = "https://www.federalreserve.gov" + href if href.startswith("/") else href
                
                all_articles.append({
                    "title": title,
                    "link": full_link,
                    "published": published,
                    "source": "FRB_Archive"
                })
                count += 1
            
            print(f"   ✅ Found {count} articles.")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Save
    if all_articles:
        df = pd.DataFrame(all_articles)
        # Deduplicate by link
        df.drop_duplicates(subset=['link'], inplace=True)
        
        mode = 'w' # Overwrite for now to get a clean archive
        df.to_csv(OUTPUT_FILE, mode=mode, header=True, index=False)
        print(f"💾 Saved {len(df)} articles to {OUTPUT_FILE}")
    else:
        print("⚠️ No articles found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2006, help="Start Year")
    parser.add_argument("--end", type=int, default=2025, help="End Year")
    args = parser.parse_args()
    
    fetch_fed_archive(start_year=args.start, end_year=args.end)
