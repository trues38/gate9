import requests
import json
import os
import time
import re
from datetime import datetime, timedelta

# Config
DATA_DIR = "nba_data"
STORIES_DIR = os.path.join(DATA_DIR, "stories_raw")
os.makedirs(STORIES_DIR, exist_ok=True)

# Date Range: Current Season Start (approx Oct 22, 2025) to Today (Dec 7, 2025)
START_DATE = "20251022"
END_DATE = "20251207"

def get_dates(start, end):
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    delta = e - s
    return [(s + timedelta(days=i)).strftime("%Y%m%d") for i in range(delta.days + 1)]

def fetch_scoreboard(date_str):
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except:
        return None

def fetch_recap(game_id):
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None
        data = resp.json()
        story = data.get('article', {})
        return story
    except:
        return None

def clean_html(raw_html):
    text = re.sub(r'<[^>]+>', '', raw_html)
    return text.replace("&nbsp;", " ").strip()

def main():
    dates = get_dates(START_DATE, END_DATE)
    print(f"🗓️  Fetching Missing Games: {START_DATE} -> {END_DATE} ({len(dates)} days)")
    
    total_saved = 0
    
    for d in dates:
        print(f"Processing {d}...", end="\r")
        sb = fetch_scoreboard(d)
        if not sb: continue
        
        events = sb.get('events', [])
        for evt in events:
            game_id = evt['id']
            # Check if exists
            fname = f"story_{game_id}.json"
            if os.path.exists(os.path.join(STORIES_DIR, fname)):
                continue
                
            # Fetch Recap
            story = fetch_recap(game_id)
            if not story or not story.get('story'):
                continue
                
            headline = story.get('headline', 'No Headline')
            body = clean_html(story.get('story', ''))
            
            # Metadata
            competitors = evt['competitions'][0]['competitors']
            t1 = competitors[0]['team']['abbreviation']
            t2 = competitors[1]['team']['abbreviation']
            matchup = f"{t1} vs {t2}"
            
            payload = {
                "game_id": game_id,
                "espn_id": game_id, # Same for direct fetch
                "date": datetime.strptime(d, "%Y%m%d").strftime("%b %d, %Y"),
                "matchup": matchup,
                "headline": headline,
                "body": body,
                "source": "espn_direct_latest",
                "crawled_at": time.time()
            }
            
            with open(os.path.join(STORIES_DIR, fname), 'w') as f:
                json.dump(payload, f, indent=2)
                
            total_saved += 1
            time.sleep(0.2) # Polite delay
            
    print(f"\n✅ Mission Complete. Downloaded {total_saved} new game narratives.")

if __name__ == "__main__":
    main()
