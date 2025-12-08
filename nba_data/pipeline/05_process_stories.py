import json
import os
import re
import glob
import logging
from collections import defaultdict
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
DATA_DIR = "nba_data"
RAW_DIR = os.path.join(DATA_DIR, "stories_raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "stories_processed")
MASTER_LIST_PATH = os.path.join(DATA_DIR, "master_list.json")
OS_PATH = os.path.join(DATA_DIR, "pipeline", "05_process_stories.py")

os.makedirs(PROCESSED_DIR, exist_ok=True)

class Normalizer:
    def __init__(self, master_list_path):
        self.player_map = {} # "LeBron James" -> "PLAYER_2544"
        self.team_map = {}   # "Bulls" -> "TEAM_CHI"
        self.load_master_list(master_list_path)
        self.init_team_map()

    def load_master_list(self, path):
        if not os.path.exists(path):
            logging.warning("Master list not found. Player normalization will be limited.")
            return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                # Assuming data is list of players from nba_api
                for p in data:
                    full_name = p['full_name']
                    pid = p['id']
                    
                    # Add full name
                    self.player_map[full_name.lower()] = f"PLAYER_{pid}"
                    
                    # Add last name? (Risk of collision, handle carefully or skip for v1)
                    # For v1, strict full name matching or basic first+last.
                    # Let's execute simple full name mapping for now.
        except Exception as e:
            logging.error(f"Error loading master list: {e}")

    def init_team_map(self):
        # Basic hardcoded map for now, can be expanded
        teams = {
            "ATL": "TEAM_ATL", "BKN": "TEAM_BKN", "BOS": "TEAM_BOS", "CHA": "TEAM_CHA",
            "CHI": "TEAM_CHI", "CLE": "TEAM_CLE", "DAL": "TEAM_DAL", "DEN": "TEAM_DEN",
            "DET": "TEAM_DET", "GSW": "TEAM_GSW", "HOU": "TEAM_HOU", "IND": "TEAM_IND",
            "LAC": "TEAM_LAC", "LAL": "TEAM_LAL", "MEM": "TEAM_MEM", "MIA": "TEAM_MIA",
            "MIL": "TEAM_MIL", "MIN": "TEAM_MIN", "NOP": "TEAM_NOP", "NYK": "TEAM_NYK",
            "OKC": "TEAM_OKC", "ORL": "TEAM_ORL", "PHI": "TEAM_PHI", "PHX": "TEAM_PHX",
            "POR": "TEAM_POR", "SAC": "TEAM_SAC", "SAS": "TEAM_SAS", "TOR": "TEAM_TOR",
            "UTA": "TEAM_UTA", "WAS": "TEAM_WAS",
            "HAWKS": "TEAM_ATL", "NETS": "TEAM_BKN", "CELTICS": "TEAM_BOS", "HORNETS": "TEAM_CHA",
            "BULLS": "TEAM_CHI", "CAVALIERS": "TEAM_CLE", "MAVERICKS": "TEAM_DAL", "NUGGETS": "TEAM_DEN",
            "PISTONS": "TEAM_DET", "WARRIORS": "TEAM_GSW", "ROCKETS": "TEAM_HOU", "PACERS": "TEAM_IND",
            "CLIPPERS": "TEAM_LAC", "LAKERS": "TEAM_LAL", "GRIZZLIES": "TEAM_MEM", "HEAT": "TEAM_MIA",
            "BUCKS": "TEAM_MIL", "TIMBERWOLVES": "TEAM_MIN", "PELICANS": "TEAM_NOP", "KNICKS": "TEAM_NYK",
            "THUNDER": "TEAM_OKC", "MAGIC": "TEAM_ORL", "76ERS": "TEAM_PHI", "SIXERS": "TEAM_PHI", 
            "SUNS": "TEAM_PHX", "TRAIL BLAZERS": "TEAM_POR", "KINGS": "TEAM_SAC", "SPURS": "TEAM_SAS",
            "RAPTORS": "TEAM_TOR", "JAZZ": "TEAM_UTA", "WIZARDS": "TEAM_WAS"
        }
        for k, v in teams.items():
            self.team_map[k.lower()] = v

class RuleTagger:
    def __init__(self):
        self.rules = [
            # STATS
            ("TripleDouble", r"triple-double|10\+ pts/reb/ast|double digits in three categories"),
            ("CareerHigh", r"career high|career-high|personal best|most points in a game"),
            ("DoubleDouble", r"double-double"),
            # SHOOTING
            ("HotShooting", r"on fire|could not miss|shooting clinic|hot hand|lights out"),
            ("ThreePointExplosion", r"raining threes|barrage of threes|from deep|beyond the arc"),
            ("ClutchShot", r"buzzer beater|game[- ]winner|final seconds|at the horn|clutch shot"),
            # HEALTH
            ("InjuryReport", r"left the game|sprained|strained|did not return|limped off|injury"),
            ("ReturnFromInjury", r"season debut|returned from|back in action|cleared to play"),
            # MOMENTUM
            ("LateCollapse", r"blew a lead|squandered|collapse|choked|gave up a.+lead"),
            ("EarlyRun", r"jumped out to|early lead|fast start|opened with a run"),
            ("MomentumShift", r"rally|erased deficit|fought back|comeback|turn the tide"),
            # CONTEXT
            ("PhysicalGame", r"flagrant|ejected|technical foul|shoving|altercation|heated"),
            ("FoulTrouble", r"foul trouble|fouled out|plagued by fouls"),
            ("PlayoffContext", r"playoff implication|clinch|eliminated|postseason spot"),
            ("Streak", r"winning streak|losing streak|straight wins|straight losses"),
            ("CoachComment", r"coach.+said|praised|blasted|frustrated with"),
            ("Rivalry", r"rivalry|grudge match|rematch|bad blood")
        ]

    def extract_tags(self, text):
        tags = set()
        text_lower = text.lower()
        for tag_name, pattern in self.rules:
            if re.search(pattern, text_lower):
                tags.add(tag_name)
        return list(tags)

class RegimeClassifier:
    """
    Maps tags to the 6 Regime Axes.
    """
    def __init__(self):
        self.mapping = {
            "Performance": ["TripleDouble", "CareerHigh", "HotShooting", "DoubleDouble"],
            "Momentum": ["LateCollapse", "EarlyRun", "MomentumShift", "Streak"],
            "Narrative": ["Rivalry", "CoachComment", "PlayoffContext", "ClutchShot"],
            "Health": ["InjuryReport", "ReturnFromInjury"],
            "Tactical": ["FoulTrouble", "PhysicalGame", "ThreePointExplosion"],
            "Variance": ["ClutchShot", "MomentumShift"] # Overlaps allowed
        }
        
    def classify(self, tags):
        regime_state = {
            "Performance": "Plateau",
            "Momentum": "Stable",
            "Narrative": "Standard",
            "Health": "Stable",
            "Tactical": "Standard",
            "Variance": "Low"
        }
        
        # Simple heuristic: if any tag in a category is present, update state
        # (Real engine would use weighted vectors, this is v1 rule-based)
        
        if any(t in tags for t in self.mapping["Performance"]):
            regime_state["Performance"] = "Surge"  # Simplified
        if "LateCollapse" in tags:
            regime_state["Momentum"] = "Collapse"
        elif "MomentumShift" in tags:
            regime_state["Momentum"] = "Comeback"
            
        if "Rivalry" in tags or "PlayoffContext" in tags:
            regime_state["Narrative"] = "HighStakes"
            
        if "InjuryReport" in tags:
            regime_state["Health"] = "InjuryRisk"
        elif "ReturnFromInjury" in tags:
            regime_state["Health"] = "ReturnBoost"
            
        if "PhysicalGame" in tags:
            regime_state["Tactical"] = "Physical"
            
        return regime_state


# ... existing classes ...

CHUNKS_DIR = os.path.join(DATA_DIR, "stories_chunks")
os.makedirs(CHUNKS_DIR, exist_ok=True)

class Chunker:
    """
    Splits text into chunks for Vector Tagging.
    Simple paragraph splitter for v1.
    """
    def __init__(self):
        pass

    def chunk_text(self, text, game_id):
        # Split by double newline (paragraphs) for ESPN stories
        raw_chunks = [c.strip() for c in text.split('\n\n') if c.strip()]
        
        chunk_objects = []
        for i, content in enumerate(raw_chunks):
            # Skip very short chunks (captions, metadata)
            if len(content) < 30: continue
            
            chunk_id = f"{game_id}_{i+1:03d}"
            
            # Simple role heuristic
            role = "body"
            if i == 0: role = "lead"
            elif i == len(raw_chunks) - 1: role = "closing"
            
            chunk_objects.append({
                "game_id": game_id,
                "chunk_id": chunk_id,
                "order": i + 1,
                "role": role,
                "text": content
            })
            
        return chunk_objects


def clean_text(text):
    """
    Clean text but preserve paragraph structure for chunking.
    """
    # Remove HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize double newlines (paragraphs)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Normalize internal bad whitespace but keep newlines
    # Use splitlines to handle per-line cleaning
    lines = [line.strip() for line in text.split('\n')]
    # Rejoin with newlines
    text = '\n'.join(lines)
    # Collapse multiple newlines to just 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_story(file_path, normalizer, tagger, classifier, chunker):
    try:
        with open(file_path, 'r') as f:
            raw_data = json.load(f)
            
        body = raw_data.get('body', '')
        game_id = raw_data.get('game_id')
        if not body or not game_id: return None
        
        # 1. Clean
        clean_body = clean_text(body)
        
        # 2. Tag
        tags = tagger.extract_tags(clean_body)
        
        # 3. Regime
        regime = classifier.classify(tags)
        
        # 4. Chunking (New Step)
        chunks = chunker.chunk_text(clean_body, game_id)
        
        # Save chunks to JSONL
        if chunks:
            chunk_path = os.path.join(CHUNKS_DIR, f"{game_id}.jsonl")
            with open(chunk_path, 'w') as f:
                for c in chunks:
                    f.write(json.dumps(c) + "\n")
        
        # 4. Normalize (Teams/Players) - placeholder
        
        processed_data = {
            "game_id": raw_data.get('game_id'),
            "espn_id": raw_data.get('espn_id'),
            "date": raw_data.get('date'),
            "matchup": raw_data.get('matchup'),
            "headline": raw_data.get('headline'),
            "cleaned_body": clean_body,
            "tags_rule": tags,
            "regime_output": regime,
            "processed_at": datetime.now().isoformat(),
            "pipeline_version": "v1"
        }
        
        return processed_data
        
    except Exception as e:
        logging.error(f"Failed to process {file_path}: {e}")
        return None

def main():
    print("Starting Story Processing Pipeline v1...")
    
    # Init engines
    normalizer = Normalizer(MASTER_LIST_PATH)
    tagger = RuleTagger()
    classifier = RegimeClassifier()
    chunker = Chunker() # New
    
    files = glob.glob(os.path.join(RAW_DIR, "story_*.json"))
    print(f"Found {len(files)} raw stories.")
    
    processed_count = 0
    
    for item in files:
        result = process_story(item, normalizer, tagger, classifier, chunker)
        if result:
            out_path = os.path.join(PROCESSED_DIR, os.path.basename(item))
            with open(out_path, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            processed_count += 1
            
        if processed_count % 100 == 0:
            print(f"Processed {processed_count}/{len(files)}")
            
    print(f"Complete. Processed {processed_count} files.")

if __name__ == "__main__":
    main()
