
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
INPUT_PATH = "processed/master_chronicle_index.json"
OUTPUT_JSONL = "processed/oracle_chronicles_test.jsonl"
OUTPUT_MD = "reports/oracle_manifesto_test.md"

def run_oracle():
    print("🔮 THE ORACLE AWAKENS: Test Mode (Batch 5)")
    
    # 1. Load Data
    with open(INPUT_PATH, 'r') as f:
        master_data = json.load(f)
        
    # Convert to DataFrame for easier handling if needed, or just list
    # Let's filter for a recent subset to ensure we have "Modern" games
    # Limit for testing?
    # batch = records[-5:] 
    target_games = master_data # FULL RUN
    
    print(f"📚 Loaded Master Index. Processing {len(target_games)} games.")
    
    # 2. Init Engine
    engine = EmergentNarrativeEngine("processed/master_chronicle_index.json") # Path arg is legacy but required
    
    # Define output paths for the full run
    output_file = "processed/oracle_chronicles_full.jsonl"
    manifesto_path = "reports/oracle_manifesto_full.md"
    
    # RESUME LOGIC ------------------------------------------------------
    processed_ids = set()
    if os.path.exists(output_file):
        print(f"🔄 Found existing chronicles file. Checking for resume...")
        try:
            with open(output_file, 'r') as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        # Assuming 'game_id' is a unique identifier for each game
                        # If not present, this resume logic will not filter
                        if 'game_id' in rec: 
                            processed_ids.add(rec['game_id'])
                    except:
                        pass # Skip malformed lines
        except Exception as e:
            print(f"⚠️ Error reading existing file: {e}")
            
    print(f"✅ Found {len(processed_ids)} already processed games.")
    
    # Filter target_games
    initial_count = len(target_games)
    # Assuming 'game_id' is present in each game dictionary in target_games
    # If not present, this resume logic will not filter
    target_games = [g for g in target_games if g.get('game_id') not in processed_ids]
    remaining_count = len(target_games)
    
    print(f"📉 Resuming Operation. {initial_count} total -> {remaining_count} remaining.")
    
    if remaining_count == 0:
        print("🎉 All games processed! Nothing to do.")
        return

    # 4. Run Oracle (Parallel Mode)
    # -------------------------------------------------------------------
    # We use ThreadPoolExecutor because the bottleneck is Network I/O (LLM API)
    # ChromaDB (Read) is thread-safe enough for this.
    
    import concurrent.futures
    import threading
    
    LOCK = threading.Lock()
    WORKERS = 10 # Adjust based on Rate Limits
    
    print(f"🔮 Oracle Engine Start. Target: {len(target_games)} games. Workers: {WORKERS}")
    
    # Files are opened once in main, passed or accessed via closure? 
    # Better to open consistently.
    
    # Open files in append mode
    # For test mode, we still overwrite MD.
    if os.path.exists(OUTPUT_MD):
        os.remove(OUTPUT_MD)
    
    f_out = open(output_file, 'a')
    f_md = open(OUTPUT_MD, 'a')
    
    # Write Header to MD
    f_md.write("# 📜 THE ORACLE MANIFESTO (TEST RUN)\n")
    f_md.write(f"Generated at: {datetime.now()}\n\n")
    f_md.write("---\n\n")
    f_md.flush()

    def process_single_game(game_meta):
        try:
            # 1. Get Context (RAG)
            context_items = engine.get_historical_context(game_meta, k=3)
            
            # 2. Generate Prophecy (LLM)
            prophecy = engine.generate_commentary(game_meta, context_items)
            
            if not prophecy:
                return None
                
            # 3. Enrich Data
            # Note: generate_commentary returns a string (the prophecy text)
            # context_items is a list of dicts (from library)
            
            game_meta['story_prophecy'] = prophecy
            game_meta['story_echoes'] = [
                {
                    'story_headline': item.get('story_headline'),
                    'edge_score': item.get('edge_score'),
                    'date': item.get('date')
                } 
                for item in context_items if isinstance(item, dict)
            ]
            
            # Pulse is just the game's own stats
            game_meta['story_pulse'] = {
                'score': game_meta.get('edge_score', 'N/A'),
                'flow': game_meta.get('flow_state', 'N/A')
            }
            
            # 4. Write to Disk (Thread-Safe)
            with LOCK:
                # JSONL
                rec_str = json.dumps(game_meta)
                f_out.write(rec_str + "\n")
                f_out.flush()
                
                # MD
                echo_text = ", ".join([f"*{item['story_headline']}*" for item in game_meta['story_echoes']])
                pulse_summ = f"Edge {game_meta['story_pulse']['score']} ({game_meta['story_pulse']['flow']})"
                
                f_md.write(f"\n### {game_meta['date']} | {game_meta['matchup']}\n")
                f_md.write(f"- **Pulse**: {pulse_summ}\n")
                f_md.write(f"- **Echoes**: {echo_text}\n")
                f_md.write(f"> **\"{prophecy}\"**\n")
                f_md.write(f"\n---\n")
                f_md.flush()
                
            return 1 # Success
        except Exception as e:
            print(f"⚠️ Error on {game_meta.get('matchup', 'Unknown')}: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Error on {game_meta.get('matchup', 'Unknown')}: {e}")
            return None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
            # Map returns an iterator, tqdm wraps it
            # We use distinct futures to update tqdm
            futures = [executor.submit(process_single_game, game) for game in target_games]
            
            for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                pass # Just checking progress
    finally:
        f_out.close()
        f_md.close()

    print(f"\n✅ Mission Complete. Prophecies saved to {manifesto_path}")

if __name__ == "__main__":
    run_oracle()
