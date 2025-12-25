import requests
import json
import os
import time
import re
from datetime import datetime, timedelta, date

# Configuration
STORIES_DIR = "nba_data/stories_raw"
os.makedirs(STORIES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

START_DATE = date(2025, 11, 1)
# END_DATE = date.today() - timedelta(days=1) # Until yesterday
END_DATE = date(2025, 12, 10) # As per current context

def fetch_espn_scoreboard(target_date):
    date_str = target_date.strftime('%Y%m%d')
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"❌ Scoreboard Error {date_str}: {e}")
        return None

def fetch_espn_recap(espn_game_id):
    api_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={espn_game_id}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        data = resp.json()
        article = data.get('article', {})
        story_html = article.get('story', '')
        
        if not story_html:
            return None, None

        headline = article.get('headline', '')
        # Clean HTML 
        text = re.sub(r'<[^>]+>', '', story_html) 
        text = text.replace("&nbsp;", " ")
        text = text.strip()
        
        return text, headline
    except:
        return None, None

def main():
    stats = {"Saved": 0, "Exists": 0, "NoStory": 0, "Total": 0}
    
    curr = START_DATE
    while curr <= END_DATE:
        print(f"📅 Scanning {curr}...")
        sb = fetch_espn_scoreboard(curr)
        if not sb: 
            curr += timedelta(days=1)
            continue
            
        events = sb.get('events', [])
        for event in events:
            # Check status
            if event['status']['type']['state'] != 'post':
                continue
                
            espn_id = event['id']
            # Game info for filename
            try:
                short_name = event['shortName'] # "PHI @ BOS"
                # sanitized
                short_name = short_name.replace(" @ ", "_vs_").replace(" ", "")
            except:
                short_name = espn_id
                
            game_date_str = curr.strftime("%Y-%m-%d")
            
            # We save using ESPN ID now, but also maybe keep the date mapping
            # The vectorizer usually reads the content.
            # Filename: story_{ESPN_ID}.json
            save_path = os.path.join(STORIES_DIR, f"story_{espn_id}.json")
            
            if os.path.exists(save_path):
                # Basic check
                try:
                    with open(save_path) as f:
                        if json.load(f).get('body'):
                            stats["Exists"] += 1
                            continue
                except:
                    pass

            # Fetch
            body, headline = fetch_espn_recap(espn_id)
            stats["Total"] += 1
            
            if not body:
                print(f"   ❌ [NoStory] {short_name} ({espn_id})")
                stats["NoStory"] += 1
                continue
            
            # Save
            story_data = {
                "game_id": espn_id, # This is the KEY for Vector DB
                "date": game_date_str,
                "headline": headline,
                "body": body,
                "source": "espn_api",
                "crawled_at": time.time()
            }
            
            with open(save_path, 'w') as f:
                json.dump(story_data, f, indent=2, ensure_ascii=False)
                
            print(f"   ✅ [Saved] {short_name}: {headline[:30]}...")
            stats["Saved"] += 1
            time.sleep(0.1)
            
        curr += timedelta(days=1)
        
    print(f"\n🚀 Backfill Complete. Stats: {stats}")

if __name__ == "__main__":
    main()
