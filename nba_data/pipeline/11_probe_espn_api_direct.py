import requests
import json
import time

def check_date(date_str, description):
    print(f"\n📅 Probing Date: {date_str} ({description})...")
    
    # 1. Get Scoreboard for Date
    scoreboard_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(scoreboard_url)
        data = resp.json()
        
        events = data.get('events', [])
        if not events:
            print("   [MISS] No events found in scoreboard.")
            return

        print(f"   [FOUND] {len(events)} games on this date.")
        
        # Pick the first game to probe
        target_event = events[0]
        game_id = target_event['id']
        name = target_event['name']
        print(f"   [GAME] {name} (ID: {game_id})")
        
        # 2. Check Summary for Story
        summary_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        resp_sum = requests.get(summary_url)
        data_sum = resp_sum.json()
        
        article = data_sum.get('article', {})
        story = article.get('story', '')
        headline = article.get('headline', 'No Headline')
        
        if story:
            print(f"   [SUCCESS] Story Found! ({len(story)} chars)")
            print(f"   [HEADLINE] {headline}")
            print(f"   [SNIPPET] {story[:100]}...")
        else:
            print("   [EMPTY] Game found, but no story text in API.")
            
    except Exception as e:
        print(f"   [ERROR] {e}")

def run_probe():
    # Test 1: Start of 2010-11 Season (Is this the missing link?)
    check_date("20101026", "2010-11 Opening Night")
    time.sleep(1)
    
    # Test 2: 2008 Finals (Big 3 Era)
    check_date("20080617", "2008 Finals G6")
    time.sleep(1)
    
    # Test 3: 2006 Christmas
    check_date("20061225", "2006 Christmas")

if __name__ == "__main__":
    run_probe()
