
import requests
import json
import datetime

# ESPN Hidden API: Scoreboard
# URL Pattern: https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD

def test_espn_api(date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    print(f"📡 Fetching: {url}")
    
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get('events', [])
            print(f"✅ Success! Found {len(events)} events for {date_str}.")
            
            for evt in events:
                game_id = evt.get('id')
                name = evt.get('name')
                links = evt.get('links', [])
                recap_link = next((l['href'] for l in links if 'recap' in l.get('rel', [])), None)
                
                print(f" - [{game_id}] {name}")
                
                # Check for headlines directly in the feed
                comps = evt.get('competitions', [])
                if comps:
                    headlines = comps[0].get('headlines', [])
                    if headlines:
                        hl = headlines[0]
                        print(f"   📰 Headline (Short): {hl.get('shortLinkText')}")
                        print(f"   📰 Headline (Desc): {hl.get('description')}")
                
                if recap_link:
                    print(f"   🔗 Recap: {recap_link}")
        else:
            print(f"❌ Failed: {resp.status_code}")
            
    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    # Test a random past date (e.g., 2023-11-15)
    test_espn_api("20231115")
