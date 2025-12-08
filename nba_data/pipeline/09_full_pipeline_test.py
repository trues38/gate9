import json
import os
import sys
import importlib.util

# -------------------------------
# 1. SETUP & IMPORTS
# -------------------------------
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

print("⏳ Loading Modules...")
regime_pkg = load_module("regime_engine", "nba_data/pipeline/07_regime_engine.py")
report_pkg = load_module("report_generator", "nba_data/pipeline/08_report_generator.py")

RegimeEngine = regime_pkg.RegimeEngine
ReportGenerator = report_pkg.ReportGenerator

# -------------------------------
# 2. DATA LOADING
# -------------------------------
GAME_ID = "0021100021"
RAW_FILE = f"nba_data/stories_raw/story_{GAME_ID}.json"
VECTOR_FILE = f"nba_data/stories_vector_tags/{GAME_ID}.jsonl"

def run_pipeline():
    print(f"\n🚀 STARTING END-TO-END PIPELINE TEST for Game {GAME_ID}")
    
    # A. Load Metadata
    print(f"   Reading metadata from {RAW_FILE}...")
    try:
        with open(RAW_FILE, 'r') as f:
            raw_data = json.load(f)
            game_meta = {
                "game_id": raw_data.get("game_id", GAME_ID),
                "matchup": raw_data.get("matchup", "Unknown Matchup"),
                "date": raw_data.get("date", "Unknown Date"),
                "headline": raw_data.get("headline", "")
            }
            print(f"   [OK] {game_meta['matchup']} ({game_meta['date']})")
    except Exception as e:
        print(f"   [ERROR] Could not load raw file: {e}")
        return

    # B. Load Vectors
    print(f"   Reading vectors from {VECTOR_FILE}...")
    chunks = []
    try:
        with open(VECTOR_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        print(f"   [OK] Loaded {len(chunks)} vector chunks.")
    except Exception as e:
        print(f"   [ERROR] Could not load vector file: {e}")
        return

    # C. Mock Player History (Simulated for Demo)
    # In real system, this comes from 'fetch_gamelogs.py' DB
    player_history = {
        "tag_scores": [0.4, 0.5, 0.45, 0.6, 0.55, 0.7, 0.8, 0.75, 0.9, 0.85], # Upward trend
        "health_scores": [0.0, -0.1, -0.2, -0.3, -0.2, -0.1, 0.0, 0.1, 0.1, 0.1] # Recovering
    }
    
    # -------------------------------
    # 3. EXECUTION
    # -------------------------------
    
    # Step 1: Regime Engine
    print("\n🧠 STEP 1: Running Regime Engine (The Brain)...")
    engine = RegimeEngine()
    regime_output = engine.process_game(chunks, player_history)
    print(f"   [RESULT] Momentum: {regime_output['momentum']}")
    print(f"   [RESULT] Health:   {regime_output['health']}")
    
    # Extract raw tags just for prompt context (top 20 relevant ones)
    all_tags = []
    for c in chunks:
        t = c.get("vector_tags", {})
        if isinstance(t, dict):
            # Flatten simple true keys or string values
            for k,v in t.items():
                if v and v != "Neutral": all_tags.append(f"{k}:{v}")
    
    # Step 2: Report Generator
    print("\n📝 STEP 2: Generating Report (The Writer) [Llama 3.3 Free]...")
    generator = ReportGenerator()
    report_text = generator.generate(
        game_meta,
        regime_output,
        {"Trend": "Mocked: Star Player averaging 28.5ppg over last 10, efficiency rising."},
        all_tags,
        regime_output["narrative_vector"]
    )
    
    # -------------------------------
    # 4. OUTPUT
    # -------------------------------
    print("\n" + "="*60)
    print("🏆 FINAL AI REGIME REPORT")
    print("="*60)
    print(f"HEADLINE: {game_meta['headline']}")
    print("-" * 60)
    print(report_text)
    print("="*60)

if __name__ == "__main__":
    run_pipeline()
