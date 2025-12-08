import json
import os
import sys

# Add path to find the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


# Actually just import directly assuming python path is usually root
# But since we are int /Users/js/g9, and script is in nba_data/pipeline
# better to use relative import or prompt python to run as module.
# Let's try direct import by path hack for simplicity in this temp script.

import importlib.util

# Load module dynamically because of "07_" prefix
spec = importlib.util.spec_from_file_location("regime_engine", "nba_data/pipeline/07_regime_engine.py")
regime_module = importlib.util.module_from_spec(spec)
sys.modules["regime_engine"] = regime_module
spec.loader.exec_module(regime_module)

from regime_engine import RegimeEngine

def run_demo():
    target_file = "nba_data/stories_vector_tags/0021100021.jsonl"
    print(f"Loading {target_file}...")
    
    chunks = []
    with open(target_file, 'r') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"Loaded {len(chunks)} chunks.")
    
    # Instantiate Engine
    engine = RegimeEngine()
    
    # Mock History (Simulation of previous 5 games)
    # Let's say this player/team was trending slightly up
    history = {
        "tag_scores": [0.2, 0.3, 0.4, 0.5, 0.1], 
        "health_scores": [0.0, 0.0, 0.0, 0.0, 0.0]
    }
    
    # Process
    print("Analyzing Regime...")
    regime = engine.process_game(chunks, history)
    
    print("\n" + "="*40)
    print("🔥 AI REGIME REPORT (LIVE)")
    print("="*40)
    print(json.dumps(regime, indent=2))
    print("="*40)
    
    # Also print some of the raw tags found
    print("\nRaw Tags Detected (Sample):")
    for c in chunks[:2]:
        print("-", c.get("vector_tags"))

if __name__ == "__main__":
    run_demo()
