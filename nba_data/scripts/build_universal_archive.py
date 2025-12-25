
import json
import os
import sys
import time
import requests
import duckdb
import pandas as pd
from tqdm import tqdm
from datetime import datetime

# Environment Setup
sys.path.append(os.getcwd())
env_file = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip().strip('"').strip("'")

# Force Hardcoded Key (Safety)
if not os.getenv("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = "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"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat"

TEAM_MAP_REVERSE = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Bobcats',
    'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards', 'NJN': 'New Jersey Nets', 'NOH': 'New Orleans Hornets'
}

def get_narrative_tags(headline, body):
    prompt = f"""
    Analyze this NBA game story and extract "Narrative Tags" & "Cause".
    
    HEADLINE: {headline}
    STORY: {body[:1500]}
    
    TASK:
    Classify this game's narrative into standard NBA Archetypes.
    
    OUTPUT JSON FORMAT:
    {{
        "primary_tag": "One of [Star_Injury, Rest_Advantage, Back_to_Back, Revenge_Game, Shooting_Slump, Hot_Hand, Upset_Alert, Blowout, Clutch_Win, Comeback, Streak_Breaker, Playoff_Preview]",
        "secondary_tags": ["List", "of", "keywords"],
        "cause_class": "Reason for result (e.g. 'The Injury', 'The Sleeping Giant', 'The Hot Hand')"
    }}
    Just return the JSON.
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://antigravity.ai"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return None
    except:
        return None

def load_quant_treasury():
    print("⏳ Loading RData Treasury from DuckDB...")
    try:
        con = duckdb.connect("nba_sql.duckdb", read_only=True)
        df_quant = con.execute("SELECT * FROM rdata_treasury").fetchdf()
        con.close()
        
        # Normalize Columns to Lowercase
        df_quant.columns = df_quant.columns.str.lower()
        
        # Normalize Date/Team for Joining
        df_quant['date'] = pd.to_datetime(df_quant['date'])
        
        # Create a lookup key: YYYYMMDD_TEAM
        df_quant['lookup_key'] = df_quant.apply(
            lambda x: f"{x['date'].strftime('%Y%m%d')}_{x['team']}", axis=1
        )
        
        lookup_dict = df_quant.set_index('lookup_key').to_dict('index')
        print(f"✅ Loaded {len(df_quant)} quant records.")
        return lookup_dict
    except Exception as e:
        print(f"❌ Failed to load DuckDB: {e}")
        return {}

def load_historical_odds():
    print("⏳ Loading Historical Odds Regimes...")
    try:
        with open("regimes/historical_odds_regimes.json", "r") as f:
            data = json.load(f)
        
        lookup = {}
        for item in data:
            # key: YYYYMMDD_TEAM
            # date format in json is "YYYY-MM-DD" -> "YYYYMMDD"
            d_str = item['date'].replace("-", "")
            
            # Key for Fav
            k1 = f"{d_str}_{item['fav_team']}"
            lookup[k1] = item
            
            # Key for Und
            k2 = f"{d_str}_{item['und_team']}"
            lookup[k2] = item
            
        print(f"✅ Loaded {len(data)} odds regimes.")
        return lookup
    except Exception as e:
        print(f"⚠️ Failed to load Historical Odds: {e}")
        return {}

def run():
    print("🦄 UNIVERSAL NARRATIVE ARCHIVE BUILDER (RESUME MODE)")
    
    # 1. Load Sources
    quant_lookup = load_quant_treasury()
    odds_lookup = load_historical_odds()
    
    # 2. Scan Stories
    stories_dir = "stories_processed"
    files = sorted([f for f in os.listdir(stories_dir) if f.endswith(".json")])
    print(f"📚 Found {len(files)} stories.")
    
    # Load Existing to valid Resume
    archive_path = "processed/universal_narrative_archive.json"
    existing_ids = set()
    archive = []
    
    if os.path.exists(archive_path):
        try:
            with open(archive_path, 'r') as f:
                archive = json.load(f)
                existing_ids = {x['game_id'] for x in archive}
            print(f"⏩ Resuming... {len(archive)} already processed.")
        except:
            print("⚠️ Corrupt archive, starting fresh.")
            archive = []

    # 3. Process
    for idx, fname in enumerate(tqdm(files)):
        try:
            with open(os.path.join(stories_dir, fname), 'r') as f:
                story_data = json.load(f)
                
            game_id = story_data['game_id']
            if game_id in existing_ids:
                continue

            # Parse Date info
            try:
                dt = datetime.strptime(story_data['date'], "%b %d, %Y")
                date_str = dt.strftime("%Y%m%d")
            except:
                continue 
                
            headline = story_data.get('headline', '')
            body = story_data.get('cleaned_body', '')
            matchup = story_data.get('matchup', '') 
            
            # Identify Teams
            candidates = []
            normalized_matchup = matchup.replace(' vs. ', ' ').replace(' @ ', ' ').replace(' vs ', ' ')
            teams = normalized_matchup.split(' ')
            
            for t in teams:
                full_name = TEAM_MAP_REVERSE.get(t)
                if full_name:
                    candidates.append(full_name)
                    
            # Try Lookup (Quant First, then Odds)
            quant_data = None
            odds_regime = None
            
            for team_name in candidates:
                lookup_key = f"{date_str}_{team_name}"
                
                # Check Quant
                if not quant_data:
                    quant_data = quant_lookup.get(lookup_key)
                
                # Check Odds
                if not odds_regime:
                    odds_regime = odds_lookup.get(lookup_key)
            
            # Tagging
            tags_json_str = get_narrative_tags(headline, body)
            tags_data = {}
            if tags_json_str:
                try:
                    tags_data = json.loads(tags_json_str)
                except:
                    pass
            
            record = {
                "game_id": game_id,
                "date": dt.strftime("%Y-%m-%d"),
                "matchup": matchup,
                "story_headline": headline,
                "story_body": body[:2000],
                "narrative_tags": tags_data,
                "quant_data": quant_data,
                "odds_regime": odds_regime, # New Field
                "has_quant": (quant_data is not None) or (odds_regime is not None)
            }
            
            # Helper: Fav Pct
            if quant_data and 'edge_score' in quant_data:
                 record['fav_pct'] = (quant_data['edge_score'] / 100.0) + 0.1
            elif odds_regime:
                 # Calculate from Odds Regime
                 # If this team is fav, odds = fav_odds.
                 # If this team is und, implied ~ (1 - 1/fav_odds)? No, just use 1/fav_odds for fav.
                 # Better to trust the 'fav_odds' field directly if we can identify if we are the fav.
                 is_fav = (odds_regime['fav_team'] in candidates)
                 if is_fav:
                     opp_odds = odds_regime['fav_odds']
                     if opp_odds > 0: record['fav_pct'] = 1.0 / opp_odds
                 else:
                     # Underdog
                     record['fav_pct'] = 0.3 # Default low
            
            archive.append(record)
            
            # Save every 20
            if idx % 20 == 0:
                with open(archive_path, "w") as out:
                    json.dump(archive, out, indent=2, default=str)
                    
        except Exception as e:
            # print(f"Skipping {fname}: {e}")
            continue

    # Final Save
    with open(archive_path, "w") as out:
        json.dump(archive, out, indent=2, default=str)
        
    print(f"✅ UNIVERSE BUILT. {len(archive)} games processed.")

if __name__ == "__main__":
    run()
