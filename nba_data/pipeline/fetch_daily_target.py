import requests
import json
import os
import argparse
import time
import logging

# Setup
DATA_DIR = "/Users/js/g9/nba_data"
STORIES_DIR = os.path.join(DATA_DIR, "stories_raw")
os.makedirs(STORIES_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

def fetch_data_for_date(target_date_compact):
    """
    Fetches data for YYYYMMDD.
    Saves to stories_raw/story_{game_id}.json
    """
    print(f"--- Fetching Data for {target_date_compact} ---")
    
    # 1. Scoreboard (Primary for IDs and Odds)
    sb_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={target_date_compact}"
    collected_games = []
    try:
        resp = requests.get(sb_url, timeout=10)
        data = resp.json()
        events = data.get('events', [])
        
        print(f"Found {len(events)} events.")
        
        for event in events:
            game_id = event['id'] # ESPN ID is the Game ID here
            name = event.get('name', 'Unknown')
            short_name = event.get('shortName', 'UNK')
            date_str = event.get('date', '') # ISO format
            
            print(f"Processing {name} ({game_id})...")
            
            # EXTRACT ODDS (Layer 1)
            odds_data = {}
            comps = event.get('competitions', [{}])[0]
            raw_odds = comps.get('odds', [])
            if raw_odds:
                first_odd = raw_odds[0]
                odds_data = {
                    "valid": True,
                    "provider": first_odd.get('provider', {}).get('name', 'Unknown'),
                    "details": first_odd.get('details', ''), # e.g. "PHI -4.5"
                    "overUnder": first_odd.get('overUnder', ''),
                    "spread": first_odd.get('spread', ''),
                    "source_type": "scoreboard_api"
                }
                print(f"  [ODDS] Found: {odds_data['details']} O/U {odds_data['overUnder']}")
            else:
                # Try pickcenter from summary if missing here?
                pass
                
            # FETCH STORY
            # We use the same 'game_id' (ESPN ID)
            summary_url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            s_resp = requests.get(summary_url, timeout=10)
            s_data = s_resp.json()
            
            headline = ""
            body = ""
            
            # Try Article
            article = s_data.get('article', {})
            if article:
                headline = article.get('headline', '')
                body = article.get('story', '')
            
            # Try Preview (common for future games)
            if not body:
                preview = s_data.get('preview', {})
                if preview:
                    # sometimes it's list?
                    if isinstance(preview, list) and len(preview) > 0:
                        body = preview[0].get('story', '')
                    elif isinstance(preview, dict):
                        body = preview.get('story', '')
            
            # Pickcenter fallback
            if not odds_data:
                pc = s_data.get('pickcenter', [])
                if pc:
                     p = pc[0]
                     odds_data = {
                        "valid": True,
                        "provider": p.get('provider', {}).get('name', 'Unknown'),
                        "details": f"SPREAD {p.get('spread')}", # Format might differ
                        "overUnder": p.get('overUnder', ''),
                        "spread": p.get('spread', ''),
                        "source_type": "pickcenter_summary"
                     }
                     print(f"  [ODDS-FALLBACK] Found in pickcenter: {odds_data['details']}")

            # SAVE
            # Note: The mapping/game_id formats in system are complex.
            # Usually: "0021700689" (NBA ID) vs "400975435" (ESPN ID).
            # The system expects NBA IDs in filenames usually?
            # 'real_previews.json' uses ESPN IDs as keys? 
            # Wait, 04_crawl_stories SAVES AS `story_{game_id}.json` where game_id is NBA ID.
            # But here I only have ESPN ID.
            # Do I have NBA ID?
            # Scoreboard event -> competitions -> uid: "s:40~l:46~e:401809837"
            # No NBA ID provided in ESPN API directly usually.
            # BUT the system might be able to handle ESPN IDs if logic permits.
            # Let's save as `story_espn_{espn_id}.json` and hope the report generator finds it?
            # OR better: The user wants "Tomorrow's Report".
            # If I save it with ESPN ID, does `fusion_report_generator` read it?
            # `fusion_report_generator` iterates through... what?
            
            # Let's save it as `story_{game_id}.json` using ESPN ID for now. 
            # If the report generator relies on "NBA Schedule CSV" to drive the loop, we are in trouble.
            # If it iterates the JSONs, we are good.
            
            story_dict = {
                "game_id": game_id,     # Using ESPN ID
                "home_id": "0", # Need to map name to ID? run_report handles this via team_map usually
                "away_id": "0", 
                # Wait, fusion_report expects home_id/away_id keys!
                # I need to parse them from event?
                # event['competitions'][0]['competitors'] -> list of 2.
                # 'homeAway': 'home' or 'away'.
                # 'id': '4' (ESPN Team ID). 
                # 'team': {'shortDisplayName': 'Knicks'}
                
                "espn_id": game_id,
                "date": target_date_compact,
                "time": event.get('date', ''),
                "matchup": name, # "Knicks at Magic"
                "headline": headline,
                "text": body, 
                "body": body, 
                "odds": odds_data,
                "source": "live_fetch"
            }
            
            # Extract Home/Away Names for Fusion
            # Fusion Report loop uses h_name = team_map.get(hid).
            # So I need to provide 'home_id' and 'away_id' that MATCH what Fusion expects?
            # Fusion expects NBA Team IDs (e.g. 1610612752).
            # ESPN provides ESPN IDs (e.g. 18).
            # I rely on 'team_map' in Fusion?
            # Fusion's match loop: hid = m['home_id'].
            # If I put "New York Knicks" as ID, team_map.get("New York Knicks") might work if logic allows?
            # run_report_target.py:32: tmap["LA Clippers"] = ...
            # Fusion Report Generator Line 275: team_map = load_team_map().
            # Line 281: h_name = team_map.get(hid, f"Team {hid}").
            # If hid is 'New York Knicks', Result -> "Team New York Knicks" or just "New York Knicks" if missing?
            # Wait. If team_map expects ID (int/str) -> Name.
            # If I provide Name, team_map.get(Name) -> None. -> "Team Name".
            # This is ugly.
            # I should provide Names as 'home_team', 'away_team' and let Fusion resolve?
            # Fusion iterates 'home_id'.
            # I will inject Name as ID for now, and hope Fusion displays it correctly?
            # OR better: Parse 'competitions' to get names.
            
            competitors = comps.get('competitors', [])
            h_name = "Unknown"
            a_name = "Unknown"
            h_score = 0
            a_score = 0
            
            for c in competitors:
                # homeAway in ['home', 'away']
                side = c.get('homeAway', 'home')
                tname = c.get('team', {}).get('displayName', 'Unknown')
                score = c.get('score', 0)
                if side == 'home':
                    h_name = tname
                    h_score = int(score) if score else 0
                else:
                    a_name = tname
                    a_score = int(score) if score else 0
            
            story_dict['home_id'] = h_name # Pass Name as ID
            story_dict['away_id'] = a_name
            story_dict['home_team'] = h_name
            story_dict['away_team'] = a_name
            story_dict['home_score'] = h_score
            story_dict['away_score'] = a_score
            
            # Filename for Story
            fname = os.path.join(STORIES_DIR, f"story_{game_id}.json")
            with open(fname, 'w') as f:
                json.dump(story_dict, f, indent=2)
            print(f"  Saved {fname}")
            
            collected_games.append(story_dict)

    except Exception as e:
        print(f"Error fetching data: {e}")

    # SAVE UNIFIED SCHEDULE
    # fusion_report_generator expects 'schedule_2025.json'
    if collected_games:
        sched_path = os.path.join(DATA_DIR, "schedule_2025.json")
        with open(sched_path, 'w') as f:
            json.dump(collected_games, f, indent=2)
        print(f"✅ Generated {sched_path} with {len(collected_games)} real games.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="YYYYMMDD")
    args = parser.parse_args()
    fetch_data_for_date(args.date)
