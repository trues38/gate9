import json
import os
import numpy as np
from datetime import datetime
import glob
from tqdm import tqdm

class PlayerRegimeEngine:
    """
    Phase 1: Current Regime Calculator.
    - Momentum: Surging/Slumping
    - Health: Risk/Fatigue
    - Narrative: Context
    - Performance: Trend
    """
    
    # ---------------------------
    # SCORING WEIGHTS
    # ---------------------------
    TAG_WEIGHTS = {
        # Positive Momentum
        "MomentumShift": 1.5, "Surge": 1.2, "HotStreak": 1.0, 
        "Clutch": 1.0, "DominantArc_Comeback": 1.5,
        "EmotionalTone_Euphoric": 0.8,
        
        # Negative Momentum
        "Collapse": -1.5, "ColdStreak": -1.2, "Fatigue": -0.5,
        "EmotionalTone_Desperate": -0.8,
        
        # Health Signals
        "InjuryReport": -2.0, "MinorKnock": -0.8, "LoadManagement": -0.5,
        
        # Performance Indicators (Indirectly via Narrative)
        "TripleDouble": 1.5, "DoubleDouble": 0.5, "RecordBreaking": 2.0
    }

    def __init__(self, data_dir="nba_data"):
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "regimes")
        os.makedirs(self.output_dir, exist_ok=True)

    def calculate_rolling_score(self, games, window=10):
        """Calculates weighted average score of last N games."""
        if not games: return 0.0
        
        recent = games[-window:]
        total_score = 0
        
        for g in recent:
            g_score = 0
            tags = g.get('vector_tags', {})
            
            # Helper to flatten dict/list tags
            flattened = []
            if isinstance(tags, dict):
                for k, v in tags.items():
                    if isinstance(v, str): flattened.append(f"{k}_{v}")
                    elif isinstance(v, bool) and v: flattened.append(k)
                    elif isinstance(v, list): flattened.extend(v)
            
            for tag in flattened:
                # Fuzzy match weights
                for w_key, w_val in self.TAG_WEIGHTS.items():
                    if w_key in tag:
                        g_score += w_val
            
            total_score += g_score
            
        return total_score / len(recent)

    def determine_regime_label(self, momentum_score, health_score):
        """Classifies the numerical scores into human-readable labels."""
        # Momentum Label
        if momentum_score > 0.8: m_label = "🔥 Surging"
        elif momentum_score > 0.3: m_label = "📈 Ascending"
        elif momentum_score < -0.8: m_label = "🥶 Slumping"
        elif momentum_score < -0.3: m_label = "📉 Descending"
        else: m_label = "⚖️ Stable"
        
        # Health Label
        if health_score < -1.0: h_label = "🚑 Injury Alert"
        elif health_score < -0.5: h_label = "⚠️ Fatigue Warning"
        else: h_label = "✅ Healthy"
        
        return m_label, h_label

    def analyze_player(self, player_id):
        """Loads a player's history and generates their current regime."""
        path = os.path.join(self.data_dir, "players", f"{player_id}_history.json")
        if not os.path.exists(path): return None
        
        with open(path, 'r') as f:
            data = json.load(f)
            
        history = data.get('history', [])
        # Filter for vector games only
        vector_games = [g for g in history if g.get('type') == 'narrative_vector']
        # Sort by date
        vector_games.sort(key=lambda x: x.get('date', '0000'))
        
        if not vector_games: return None
        
        # 1. Momentum Score (Last 10 Games)
        momentum = self.calculate_rolling_score(vector_games, window=10)
        
        # 2. Health Score (Last 5 Games - simpler window)
        # We need specific health tags logic here, reusing general calc for now with negative weights
        # Actually existing calc handles negative weights correctly.
        health_tags_only = [
            {
                "vector_tags": {
                    k: v for k, v in g.get('vector_tags', {}).items() 
                    if any(h in k for h in ["Injury", "Fatigue", "Knock", "Load"])
                } 
            }
            for g in vector_games
        ]
        health = self.calculate_rolling_score(health_tags_only, window=5)

        # 3. Narrative Context (Last 3 Games)
        recent_tags = []
        for g in vector_games[-3:]:
            t = g.get('vector_tags', {})
            # Extract key emotional/context tags
            if isinstance(t, dict):
                arc = t.get('DominantArc')
                if arc and arc != "Neutral": recent_tags.append(arc)
                tone = t.get('EmotionalTone')
                if tone and tone != "Neutral": recent_tags.append(tone)
        
        m_label, h_label = self.determine_regime_label(momentum, health)
        
        # 4. Latent Vector (For Doppelganger Matching)
        # Average of last 10 embedding vectors
        embeddings = [g.get('embedding') for g in vector_games[-10:] if g.get('embedding')]
        if embeddings:
            latent_vector = np.mean(embeddings, axis=0).tolist()
        else:
            latent_vector = []

        return {
            "id": player_id,
            "name": data['meta']['name'],
            "regime": {
                "momentum_score": round(momentum, 2),
                "momentum_label": m_label,
                "health_score": round(health, 2),
                "health_label": h_label,
                "narrative_context": list(set(recent_tags)), # Dedupe
                "last_updated": vector_games[-1].get('date')
            },
            "latent_vector": latent_vector
        }

    def run_all(self):
        """Process all players."""
        print("🚀 REGIME ENGINE [PHASE 1]: Calculating Current States...")
        p_files = glob.glob(os.path.join(self.data_dir, "players", "*_history.json"))
        
        results = []
        for p_file in tqdm(p_files):
            pid = os.path.basename(p_file).replace("_history.json", "")
            regime = self.analyze_player(pid)
            if regime:
                results.append(regime)
                
        # Save Master Regime File
        out_path = os.path.join(self.output_dir, "current_regimes.json")
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"✅ Generated regimes for {len(results)} players.")
        print(f"📄 Saved to {out_path}")

if __name__ == "__main__":
    engine = PlayerRegimeEngine()
    engine.run_all()
