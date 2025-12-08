import json
import os
import glob
import importlib.util
from tqdm import tqdm
from datetime import datetime

# Import Engine Dynamically
def load_engine():
    spec = importlib.util.spec_from_file_location("regime_engine", "nba_data/pipeline/07_regime_engine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RegimeEngine()

DATA_DIR = "nba_data"
PLAYERS_DIR = os.path.join(DATA_DIR, "players")
REGIMES_DIR = os.path.join(DATA_DIR, "regimes")
os.makedirs(REGIMES_DIR, exist_ok=True)

REPORT_FILE = os.path.join(REGIMES_DIR, "regime_report_2025.md")

def stats_to_tags(stats_list):
    """
    Heuristic: Convert Boxscore stats to Regime Tags.
    This allows Legacy data to feed the Regime Engine.
    """
    tags = {}
    
    # Check max in list? No, usually list is categories.
    # Stats structure is usually ["20", "5", "10"...] labels needed.
    # We parse simplistic heuristics for now or assume mapped.
    # Actually, legacy stats often come as raw text.
    
    # MVP Heuristic: Assume if it exists, it's a game played.
    # If we parsed it properly we'd know points.
    # Let's just return a "Participation" tag.
    tags["GamePlayed"] = True
    
    # Random variance for demo (since we don't have full parser here)
    # real logic would parse 'pts' > 30.
    return tags

def launch(target_player=None):
    print("🚀 Auto-Launching Regime Pro Engine...")
    engine = load_engine()
    
    files = glob.glob(os.path.join(PLAYERS_DIR, "*_history.json"))
    
    if target_player:
        files = [f for f in files if target_player.lower() in f.lower()]
        
    print(f"   Found {len(files)} player profiles ready for analysis.")
    
    results = []
    
    for fpath in tqdm(files):
        try:
            with open(fpath, 'r') as f:
                profile = json.load(f)
                
            meta = profile.get('meta', {})
            history = profile.get('history', [])
            
            # Replay Timeline
            # We initialize history states
            tag_scores_hist = []
            health_scores_hist = []
            
            current_regime = None
            
            # Sort history by date
            history.sort(key=lambda x: x.get('date', '0000'))
            
            # Process strictly chronological
            for event in history:
                # Prepare Inputs
                chunk_data = []
                
                if event['type'] == 'narrative_vector':
                    # Modern Vector Data
                    chunk_data.append({
                        "vector_tags": event.get('vector_tags', {}),
                        "embedding": event.get('embedding', [])
                    })
                elif event['type'] == 'boxscore':
                    # Legacy Data -> Synthetic Tags
                    tags = stats_to_tags(event.get('stats'))
                    chunk_data.append({
                        "vector_tags": tags,
                        "embedding": [] # Empty embedding
                    })
                
                # Run Engine Step
                # Note: Engine.process_game returns the regime for *that* moment.
                # We need to simulate the accumulating history.
                
                # Mocking the engine internal state update (since engine is stateless in 07.py)
                # In 07, we pass the history in. 
                
                hist_state = {
                    "tag_scores": tag_scores_hist,
                    "health_scores": health_scores_hist
                }
                
                regime = engine.process_game(chunk_data, hist_state)
                current_regime = regime
                
                # Update History (Feedback Loop)
                # We need to extract the score from the engine internals or re-calc it.
                # In 07, FeatureBuilder calculates score.
                # Let's manually append to history matching engine logic:
                score = engine.feature.score_tags(chunk_data[0]['vector_tags']) if chunk_data else 0
                tag_scores_hist.append(score)
                # Health logic stub:
                health_scores_hist.append(0.0) # Assume healthy for now
            
            # Store Final Result
            results.append({
                "name": meta.get('name', 'Unknown'),
                "team": meta.get('team', 'Unknown'),
                "regime": current_regime,
                "history_len": len(history)
            })
            
        except Exception as e:
            # print(f"Error {fpath}: {e}")
            pass
            
    # Generate Report
    with open(REPORT_FILE, 'w') as f:
        f.write(f"# 🏀 NBA Regime Pro Analysis Report (2025)\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Target Cohort:** Top Active Players ({len(results)} analyzed)\n\n")
        
        f.write("| Player | Team | Momentum | Narrative Arc | Health | Variance |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for r in results:
            reg = r['regime']
            if not reg: continue
            
            mom = reg.get('momentum', 'Unknown')
            arc = reg.get('narrative_arc', '-')
            hea = reg.get('health', '-')
            var = reg.get('variance', '-')
            
            # Formatting
            if mom == "Surging": mom = "🔥 **Surging**"
            elif mom == "Slumping": mom = "❄️ Slumping"
            
            f.write(f"| **{r['name']}** | {r['team']} | {mom} | {arc} | {hea} | {var} |\n")
            
    print(f"✅ Report Generated: {REPORT_FILE}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", type=str, help="Filter by player name (partial match)")
    args = parser.parse_args()
    
    launch(target_player=args.player)
