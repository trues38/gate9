import requests
import json
import time

def check_boxscore(game_id, description):
    print(f"\n📊 Probing Box Score: {description} (ID: {game_id})...")
    
    # Summary endpoint usually contains boxscore data or links to it
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    try:
        resp = requests.get(url)
        data = resp.json()
        
        # Check for Box Score / Leaders
        boxscore = data.get('boxscore', {})
        leaders = data.get('leaders', [])
        
        if boxscore or leaders:
            print(f"   [SUCCESS] Stats Found!")
            if leaders:
                l = leaders[0] # Usually top performers
                print(f"   [LEADER] {l.get('leaders', [{}])[0].get('athlete', {}).get('displayName')} (Display: {l.get('leaders', [{}])[0].get('displayValue')})")
            return True
        else:
            print("   [FAIL] No stats data found.")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

def run_probe():
    # 2010 Finals G7 (ID from previous probe: 300617013)
    check_boxscore("300617013", "2010 Finals G7")
    
    # 2003 LeBron Debut (ID: 231029002)
    check_boxscore("231029002", "2003 LeBron Debut")
    
    # 1998 Jordan Last Shot (ID: 180614026)
    check_boxscore("180614026", "1998 Finals G6")

if __name__ == "__main__":
    run_probe()
