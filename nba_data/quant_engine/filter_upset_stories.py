
import os
import json
import pandas as pd
import re
from tqdm import tqdm

DATA_DIR = "nba_data/stories_raw"
OUTPUT_FILE = "nba_data/processed/upset_candidates_regex.csv"

# Keywords that suggest an upset or narrative interest regarding expectations
UPSET_KEYWORDS = [
    r"\bupset\b", 
    r"\bstun(ned|s)?\b", 
    r"\bshock(ed|s|ing)?\b", 
    r"\bsurpris(e|ed|ing)\b", 
    r"\bunderdog\b", 
    r"\bfavorit(e|es)\b",
    r"\bodds\b",
    r"\bline\b", 
    r"\bspread\b",
    r"\bunexpected\b"
]

def filter_upsets():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    print(f"📂 Found {len(files)} stories in {DATA_DIR}")
    
    candidates = []
    
    for filename in tqdm(files):
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            headline = data.get('headline', '')
            body = data.get('body', '')
            text = headline + " " + body
            text_lower = text.lower()
            
            # Check for keywords
            matched_keywords = []
            for kw in UPSET_KEYWORDS:
                if re.search(kw, text_lower):
                    matched_keywords.append(kw.replace(r"\b", "").replace(r"(ed|s)?", ""))
            
            if matched_keywords:
                candidates.append({
                    "game_id": data.get('game_id'),
                    "date": data.get('date'),
                    "matchup": data.get('matchup'),
                    "headline": headline,
                    "matched_keywords": ", ".join(matched_keywords),
                    "filename": filename
                })
                
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            
    df = pd.DataFrame(candidates)
    print(f"🔥 Found {len(df)} candidates out of {len(files)} stories.")
    
    if not df.empty:
        # Sort by number of keywords matched (proxy for relevance)
        df['match_count'] = df['matched_keywords'].apply(lambda x: len(x.split(',')))
        df = df.sort_values('match_count', ascending=False)
        
        print("\nTop 10 Candidates:")
        print(df[['date', 'matchup', 'matched_keywords']].head(10).to_string(index=False))
        
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✅ Saved candidates to {OUTPUT_FILE}")
    else:
        print("❌ No candidates found.")

if __name__ == "__main__":
    filter_upsets()
