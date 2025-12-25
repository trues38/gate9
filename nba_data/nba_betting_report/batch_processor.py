
import os
import json
import glob
from datetime import datetime
from agents import structural_analyst, pattern_matcher, market_decision

INPUT_DIR = "nba_betting_report/input/"
OUTPUT_FILE = "nba_betting_report/regime_observations.jsonl"

def process_all_files():
    print(f"🚀 Starting batch processing from {INPUT_DIR}...")
    
    json_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    if not json_files:
        print("❌ No input files found!")
        return

    observations = []
    
    for file_path in json_files:
        # standard "sample_input.json" is not a daily file, skip if needed or just process
        if "sample_input" in file_path:
            continue
            
        print(f"  Processing {os.path.basename(file_path)}...")
        
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"    ⚠️ Error reading file: {e}")
            continue

        # 1. Structural Analyst
        #    - Validates data
        #    - Calculates derived metrics (box_stats including pace_est, efg, margins)
        try:
            struct_out = structural_analyst.analyze(raw_data)
        except Exception as e:
            print(f"    ⚠️ Structural Analyst failed: {e}")
            continue
            
        # 2. Pattern Matcher
        #    - Calculates edge_score (using struct_out's derived metrics)
        try:
            pattern_out = pattern_matcher.analyze(struct_out)
        except Exception as e:
            print(f"    ⚠️ Pattern Matcher failed: {e}")
            continue
            
        # 3. Market Decision
        #    - Determines Action (BET/PASS) and Confidence based on edge_score
        try:
            market_out = market_decision.analyze(pattern_out)
        except Exception as e:
            print(f"    ⚠️ Market Decision failed: {e}")
            continue

        # 4. Aggregate Results into Observation Records
        #    We need to join GameContext (Stats) + Pattern (Edge) + Decision (Action)
        
        contexts = {g['game_id']: g for g in struct_out['game_contexts']}
        patterns = {p['game_id']: p for p in pattern_out['game_patterns']}
        decisions = {d['game_id']: d for d in market_out['betting_decisions']}
        
        for game_id, decision in decisions.items():
            ctx = contexts.get(game_id)
            pat = patterns.get(game_id)
            
            if not ctx or not pat:
                continue
                
            observation = {
                "date": ctx['date'],
                "game_id": game_id,
                "timestamp": datetime.now().isoformat(),
                "edge_score": pat.get('edge_score'),
                "action": decision.get('action'),
                "confidence": decision.get('confidence'),
                "box_stats": ctx.get('box_stats'),  # Critical for backtest
                "pipeline_version": "v0.1"
            }
            observations.append(observation)

    # Write to JSONL
    print(f"💾 Saving {len(observations)} observations to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        for obs in observations:
            f.write(json.dumps(obs) + "\n")
            
    print("✅ Batch processing complete.")

if __name__ == "__main__":
    process_all_files()
