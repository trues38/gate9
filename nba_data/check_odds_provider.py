import requests
import json
import traceback

# Target Date: Past Date (2025-11-01) to see if history exists.
TARGET_DATE = "20251101"

def check_odds():
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={TARGET_DATE}"
    print(f"Fetching: {url}")
    
    try:
        r = requests.get(url)
        data = r.json()
        
        events = data.get('events', [])
        print(f"Events Found: {len(events)}")
        
        for event in events:
            name = event.get('name')
            print(f"\n🏀 {name}")
            
            comps = event.get('competitions', [])
            if not comps: continue
            
            odds = comps[0].get('odds', [])
            if odds:
                print(f"   ✅ Odds Available: {len(odds)} items")
                for o in odds:
                    print(f"      - Provider: {o.get('provider', {}).get('name')}")
                    print(f"      - Details: {o.get('details')}")
                    print(f"      - Over/Under: {o.get('overUnder')}")
            else:
                print("   ❌ No Odds Found (Field is empty)")
                
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    check_odds()
