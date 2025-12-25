
import pandas as pd

import json
import os
import sys
sys.path.append(os.getcwd())
from tqdm import tqdm
from datetime import datetime


# Load .env manually to ensure API Key availability in batch mode
# Hardcoded for reliability in this session
os.environ["OPENROUTER_API_KEY"] = "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"

from quant_engine_v1.emergent_narrative_engine import EmergentNarrativeEngine

# Input/Output
INPUT_PATH = "processed/backtest_results_exp1.csv"
OUTPUT_JSONL = "processed/oracle_chronicles_full.jsonl"
OUTPUT_MD = "reports/oracle_manifesto.md"

def run_oracle():
    print("🔮 THE ORACLE AWAKENS: Mass Production Mode")
    
    # 1. Load Data
    df = pd.read_csv(INPUT_PATH)
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter for 2022 Playoffs (From April 10, 2022)
    # User requested verify from "22/4/10"
    mask = df['date'] >= '2022-04-10'
    target_games = df[mask].copy()
    
    print(f"📚 Found {len(target_games)} games from 2024-2026 eras.")
    
    # 2. Init Engine
    engine = EmergentNarrativeEngine("quant_engine/upset_library_enriched.json")
    
    # Check for existing progress
    processed_count = 0
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, 'r') as f:
            processed_count = sum(1 for line in f)
    
    print(f"🔄 Resuming from game {processed_count}...")
    
    # 3. Process Loop
    results = []
    
    # Open JSONL in append mode
    with open(OUTPUT_JSONL, 'a') as f_json, open(OUTPUT_MD, 'a') as f_md:
        
        # Write Header to MD if new
        if processed_count == 0:
            f_md.write("# 📜 THE ORACLE MANIFESTO\n")
            f_md.write(f"Generated at: {datetime.now()}\n\n")
            f_md.write("---\n\n")
            
        # Iterate
        # Limit to 1 for testing
        print(f"🔮 Test Run: Checking Semantic Retrieval Integration...")

        # Use target_games instead of df
        for idx, row in target_games.iterrows():
            # Pick a specific game index if we want, or just the first one
            if idx < 5: continue
            if idx > 5: break
            
            game = row.to_dict()
            game['matchup'] = f"{row['team']} vs {row['opp']}"
            print(f"\n🔮 Processing: {game['date']} {game['matchup']}")
            
            # 1. Find Twin (Statistical)
            twin = engine.find_narrative_twin(game)
            if not twin: 
                print("No twin found.")
                continue
                
            # 2. Gen Commentary (Includes Semantic Fetch internally)
            print("⚡ Generating Commentary (calling Semantic Retriever)...")
            commentary = engine.generate_commentary(game, [twin])
            
            print("\n" + "="*50)
            print("OUTPUT COMMENTARY:")
            print(commentary)
            print("="*50 + "\n")
            
            # Original logic for saving (adapted for single run)
            game_info = {
                "matchup": f"{row['team']} vs {row['opp']}",
                "date": row['date'].strftime('%Y-%m-%d'),
                "edge_score": row['edge_score'],
                "flow_state": row['flow_state'],
                "fatigue_state": row['fatigue_state'],
                "result_actual": row['result']
            }
            
            try:
                # Find Historical Context (RAG) - using the twin found above
                context_items = [twin] # Assuming twin is the context item
                
                # Generate Prophecy - using the commentary generated above
                prophecy = commentary
                
                # Bundle
                entry = {
                    "game": game_info,
                    "context_headlines": [item['story_headline'] for item in context_items],
                    "oracle_text": prophecy
                }
                
                # Save JSONL
                f_json.write(json.dumps(entry) + "\n")
                f_json.flush()
                
                # Save MD (Pretty)
                twins_str = ", ".join([f"*{item['story_headline']}*" for item in context_items])
                md_block = f"""
### {game_info['date']} | {game_info['matchup']}
- **Pulse**: Edge {game_info['edge_score']} ({game_info['flow_state']})
- **Echoes**: {twins_str}
> **"{prophecy.strip()}"**

---
"""
                f_md.write(md_block)
                f_md.flush()
                
            except Exception as e:
                print(f"⚠️ Error on {game_info['matchup']}: {e}")
                continue

    print(f"\n✅ Mission Complete. Prophecies saved to {OUTPUT_MD}")

if __name__ == "__main__":
    run_oracle()
