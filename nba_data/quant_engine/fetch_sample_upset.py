
import requests
import json
import os
import re
import datetime

OUTPUT_FILE = "/Users/js/g9/nba_data/quant_engine/story_upset_2025.json"
SUMMARY_URL_TEMPLATE = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={}"

def fetch_any_upset():
    start_date = datetime.date(2025, 11, 15)
    
    best_upset = None
    max_pct_diff = -1.0
    
    # Iterate dates
    for i in range(10): 
        curr_date = start_date + datetime.timedelta(days=i)
        date_str = curr_date.strftime("%Y%m%d")
        print(f"Scanning {date_str}...")
        
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            events = data.get('events', [])
            
            for event in events:
                try:
                    game_id = event['id']
                    status = event['status']['type']['state']
                    if status != 'post': continue 
                    
                    competitors = event['competitions'][0]['competitors']
                    winner_comp = None
                    loser_comp = None
                    
                    for comp in competitors:
                        if comp.get('winner', False):
                            winner_comp = comp
                        else:
                            loser_comp = comp
                            
                    if not (winner_comp and loser_comp): continue
                    
                    # Parse Records
                    def get_pct(c):
                        recs = c.get('records', [])
                        s = recs[0]['summary'] if recs else "0-0"
                        if "-" in s:
                            w, l = map(int, s.split('-'))
                            return w / (w + l) if (w+l) > 0 else 0.5
                        return 0.5
                        
                    w_pct = get_pct(winner_comp)
                    l_pct = get_pct(loser_comp)
                    
                    # Check if Winner had LOWER win % than Loser (Upset)
                    if w_pct < l_pct:
                        diff = l_pct - w_pct
                        print(f"Candidate: {winner_comp['team']['abbreviation']} ({w_pct:.3f}) def {loser_comp['team']['abbreviation']} ({l_pct:.3f}) [Diff: {diff:.3f}]")
                        
                        if diff > max_pct_diff:
                            max_pct_diff = diff
                            best_upset = {
                                "game_id": game_id,
                                "date": date_str,
                                "matchup": f"{loser_comp['team']['abbreviation']} @ {winner_comp['team']['abbreviation']}", # Approximate
                                "favorite": loser_comp['team']['abbreviation'],
                                "underdog": winner_comp['team']['abbreviation'],
                                "fav_pct": round(l_pct, 3),
                                "und_pct": round(w_pct, 3),
                                "score": f"{winner_comp['score']}-{loser_comp['score']}",
                                "headline": ""
                            }
                except:
                    continue
        except Exception as e:
            print(e)
            continue

    if best_upset:
        print(f"Selected Best Upset: {best_upset['favorite']} vs {best_upset['underdog']} (Diff: {max_pct_diff:.3f})")
        # Fetch Story
        summ_url = SUMMARY_URL_TEMPLATE.format(best_upset['game_id'])
        try:
            s_resp = requests.get(summ_url, timeout=10)
            s_data = s_resp.json()
            article = s_data.get('article', {})
            story_html = article.get('story', '')
            headline = article.get('headline', '')
            
            if story_html:
                text = re.sub(r'<[^>]+>', '', story_html)
                text = text.replace("&nbsp;", " ").strip()
                best_upset['headline'] = headline
                best_upset['body'] = text
                
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(best_upset, f, indent=2)
                print(f"Saved to {OUTPUT_FILE}")
            else:
                print("No story found for this game.")
        except:
            print("Failed to fetch story.")
    else:
        print("No upset found.")

if __name__ == "__main__":
    fetch_any_upset()
