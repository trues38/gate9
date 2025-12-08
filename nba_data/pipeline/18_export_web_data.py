import json
import os
import glob
from datetime import datetime

# Paths
DATA_DIR = "nba_data"
REGIME_DIR = os.path.join(DATA_DIR, "regimes")
PLAYERS_FILE = os.path.join(REGIME_DIR, "regimes_with_dna.json")
TEAMS_FILE = os.path.join(REGIME_DIR, "team_regimes.json")
WEB_DATA_DIR = "web/public/data"
OUTPUT_FILE = os.path.join(WEB_DATA_DIR, "dashboard.json")

def load_json(path):
    if not os.path.exists(path): return []
    with open(path, 'r') as f:
        return json.load(f)

def generate_confidence_score(player_regime, team_regime):
    """
    Layer 3: The Signal.
    Combines Player Momentum + Team Stability + Historical DNA Match.
    Range: 0 - 100
    """
    score = 50.0
    
    # 1. Player Momentum
    mom = player_regime['regime']['momentum_score']
    score += mom * 20  # +1.0 -> +20, -1.0 -> -20
    
    # 2. Team Context (if available)
    if team_regime:
        t_mom = team_regime['momentum']
        score += t_mom * 10
        
        # Volatility Penalty
        if team_regime['volatility'] > 0.8:
            score -= 10 # Unpredictable team context
            
    # 3. DNA Reliability (Doppelganger Match Strength)
    dna = player_regime['regime'].get('doppelganger')
    if dna:
        top_match = dna[0]
        similarity = top_match['similarity']
        if similarity > 85: score += 10 # High confidence in historical pattern
        elif similarity > 70: score += 5
        
    # Clamp
    return max(0, min(100, int(score)))

def export_data():
    print("🚀 Exporting Regime Pro Data (Production Mode)...")
    
    # Load Engines
    players = load_json(PLAYERS_FILE)
    teams = load_json(TEAMS_FILE)
    
    # Index Teams by ID (if needed, here we rely on player team_id from metadata if possible)
    # Actually regimes_with_dna doesn't have team_id explicitly at top level, let's load meta
    meta_map = {}
    if os.path.exists("nba_data/players/top_250_active.json"):
        raw_meta = load_json("nba_data/players/top_250_active.json")
        meta_map = {p['id']: p for p in raw_meta}
        
    team_map = {t['team_id']: t for t in teams}
    
    export_list = []
    
    for p in players:
        pid = p['id']
        meta = meta_map.get(pid, {})
        tid = meta.get('team_id')
        
        # Find Team Context
        team_ctx = team_map.get(tid)
        
        # Calculate Signal
        confidence = generate_confidence_score(p, team_ctx)
        
        # Narrative extraction
        narratives = p['regime']['narrative_context']
        narrative_text = ", ".join(narratives[:3]) if narratives else "Stable Baseline"
        
        # Doppelganger Text
        dna_text = "None"
        dna_match = p['regime'].get('doppelganger')
        if dna_match:
            top = dna_match[0]
            dna_text = f"{top['name']} ({top['similarity']}%)"
        
        card = {
            "id": pid,
            "name": p['name'],
            "team": team_ctx['team_name'] if team_ctx else "Unknown",
            "status": p['regime']['momentum_label'], # "🔥 Surging"
            "vector": "Ascending" if p['regime']['momentum_score'] > 0 else "Descending", # Simplified for UI
            "momentum_score": p['regime']['momentum_score'],
            "conviction_score": confidence,
            "narrative": f"Regime: {narrative_text}. \nDNA Match: {dna_text}",
            "last_updated": p['regime']['last_updated']
        }
        export_list.append(card)
        
    # Sort by Confidence (High to Low for "High Conviction Alpha")
    export_list.sort(key=lambda x: x['conviction_score'], reverse=True)
    
    # Market Metrics
    if export_list:
        avg_conf = sum(x['conviction_score'] for x in export_list[:10]) / 10
    else:
        avg_conf = 50
        
    final_output = {
        "generated_at": datetime.now().isoformat(),
        "market_confidence": round(avg_conf, 1),
        "market_mood": "RISK_ON" if avg_conf > 70 else "CAUTIOUS",
        "total_players": len(export_list),
        "players": export_list
    }
    
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(final_output, f, indent=2)
        
    print(f"✅ Exported {len(export_list)} PRO profiles to {OUTPUT_FILE}")

if __name__ == "__main__":
    export_data()
