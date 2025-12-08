import requests
from duckduckgo_search import DDGS
import json
import time

def get_espn_id_and_check_quality(query):
    print(f"🔎 Probing: '{query}'...")
    try:
        results = DDGS().text(query, max_results=1)
        if not results:
            print("   [MISS] No search results found.")
            return None
        
        url = results[0]['href']
        print(f"   [FOUND] URL: {url}")
        
        # Extract ESPN Game ID
        # Format: espn.com/nba/recap?gameId=231029005 or /game/_/gameId/231029005
        import re
        match = re.search(r'gameId[=/](\d+)', url)
        if not match:
             match = re.search(r'/game/_/id/(\d+)', url)
        
        if not match:
            print("   [FAIL] Could not extract Game ID from URL.")
            return None
            
        espn_id = match.group(1)
        print(f"   [ID] ESPN ID: {espn_id}")
        
        # Check API
        api_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={espn_id}"
        resp = requests.get(api_url)
        data = resp.json()
        
        # Check Recap
        article = data.get('article', {})
        story = article.get('story', '')
        headline = article.get('headline', 'No Headline')
        
        if story:
            print(f"   [SUCCESS] Found Story! ({len(story)} chars)")
            print(f"   [HEADLINE] {headline}")
            print(f"   [SAMPLE] {story[:100]}...")
            return True
        else:
            print("   [EMPTY] API returned no story text.")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

def run_probe():
    # Test 1: 2010 Finals (Relaxed)
    get_espn_id_and_check_quality("site:espn.com nba recap lakers celtics june 17 2010")
    time.sleep(1)
    
    # Test 2: 2003 LeBron (Relaxed)
    get_espn_id_and_check_quality("site:espn.com nba recap cavaliers kings october 29 2003")
    time.sleep(1)
    
    # Test 3: 1998 Jordan (Relaxed - likely AP wire)
    get_espn_id_and_check_quality("site:espn.com nba recap bulls jazz june 14 1998")

if __name__ == "__main__":
    run_probe()
