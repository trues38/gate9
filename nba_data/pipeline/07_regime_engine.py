import numpy as np
from typing import List, Dict, Any

# ---------------------------------------------------
# A. FEATURE BUILDER
# ---------------------------------------------------

class FeatureBuilder:
    """
    Extracts quantitative signals from vector tags + embeddings.
    Converts 'tags' into numerical scores.
    """

    TAG_WEIGHTS = {
        "MomentumShift": 1.2,
        "Clutch": 0.8,
        "Surge": 1.0,
        "Collapse": -1.0,
        "InjuryReport": -1.2,
        "MinorKnock": -0.5,
        "DoubleDouble": 0.4,
        "TripleDouble": 0.8,
        "Ejection": -1.0,
        "Fatigue": -0.6,
        "HotStreak": 0.7,
        "ColdStreak": -0.7,
        "TacticalMismatch": 0.6,
        # Default fallback for mapped tags from LLM output
        "NarrativeIntensity_High": 0.5,
        "NarrativeIntensity_Extreme": 1.0,
        "DominantArc_Comeback": 1.0,
        "DominantArc_Blowout": 0.5,
        "DominantArc_Clutch": 1.0,
        "DominantArc_Injury": -1.5,
        "EmotionalTone_Euphoric": 0.8,
        "EmotionalTone_Desperate": -0.5,
        "EmotionalTone_Frustrated": -0.8
    }

    def score_tags(self, tags: Any) -> float:
        """Aggregate weighted tag score. 'tags' can be list or dict."""
        score = 0.0
        
        # Handle dict format (LLM JSON output)
        if isinstance(tags, dict):
            # Flatten dict keys to robust strings for matching
            # e.g. NarrativeIntensity: High -> NarrativeIntensity_High
            for k, v in tags.items():
                if isinstance(v, str):
                    key = f"{k}_{v}"
                    score += self.TAG_WEIGHTS.get(key, 0)
                elif isinstance(v, list):
                    # PlayerFocus or custom lists
                    pass
                elif isinstance(v, bool) and v:
                     score += self.TAG_WEIGHTS.get(k, 0)
        
        # Handle simple list format
        elif isinstance(tags, list):
            score = sum(self.TAG_WEIGHTS.get(tag, 0) for tag in tags)

        return score

    def vector_direction(self, vectors: List[List[float]]) -> np.ndarray:
        """Mean direction vector (narrative flow)."""
        if not vectors:
            return np.zeros(1024) # Assuming Qwen 4B/8B dimension or similar
        return np.mean(np.array(vectors), axis=0)

    def build(self, chunk_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        scores = []
        vectors = []

        for chunk in chunk_list:
            scores.append(self.score_tags(chunk.get("vector_tags", [])))
            # Handle embeddings being empty or None
            vec = chunk.get("embedding", [])
            if vec and len(vec) > 0:
                vectors.append(vec)

        return {
            "tag_scores": scores,
            "mean_vector": self.vector_direction(vectors),
            "mean_score": np.mean(scores) if scores else 0,
            "variance": np.var(scores) if scores else 0
        }


# ---------------------------------------------------
# B. SIGNAL INTEGRATOR (TIME SERIES)
# ---------------------------------------------------

class SignalIntegrator:
    """
    Combines today's signals with historical signals
    to determine the regime phase.
    """

    def trend(self, history: List[float]) -> float:
        if not history or len(history) < 3:
            return 0.0
        # Compare recent 3 avg vs recent 10 avg
        short_window = history[-3:]
        long_window = history[-10:]
        return np.mean(short_window) - np.mean(long_window)

    def classify_phase(self, mean_score: float, trend: float) -> str:
        if mean_score > 0.7 and trend > 0.3:
            return "Surging"
        if trend > 0.2:
            return "Ascending"
        if mean_score < -0.5 and trend < -0.2:
            return "Slumping"
        if abs(trend) < 0.05:
            return "Stable"
        return "Uncertain"

    def health_phase(self, health_hist: List[float]) -> str:
        if not health_hist or len(health_hist) < 3:
            return "Unknown"
        t = self.trend(health_hist)
        if t < -0.2:
            return "Deteriorating"
        if t > 0.2:
            return "Recovering"
        return "Managed"

    def integrate(self, features: Dict[str, Any], history: Dict[str, List[float]]) -> Dict[str, Any]:
        tag_scores_hist = history.get("tag_scores", [])
        # Append current score to "virtual evaluation history" for trend calc
        # In a real pipeline, we'd update the DB. Here we simulate.
        current_score = features["mean_score"]
        
        # Calculate trend including current Game
        extended_hist = tag_scores_hist + [current_score]
        tag_trend = self.trend(extended_hist)
        
        health_scores_hist = history.get("health_scores", [])
        health_phase_res = self.health_phase(health_scores_hist)

        return {
            "momentum_phase": self.classify_phase(features["mean_score"], tag_trend),
            "health_phase": health_phase_res,
            "variance": features["variance"],
            "narrative_vector": features["mean_vector"],
        }


# ---------------------------------------------------
# C. REGIME COMPOSER (FINAL OUTPUT)
# ---------------------------------------------------

class RegimeComposer:
    """
    Converts integrated signals into labels for the report layer.
    """

    def compose(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "momentum": signals["momentum_phase"],
            "health": signals["health_phase"],
            "variance": "HighVariance" if signals["variance"] > 0.8 else "LowVariance",
            "narrative_vector": signals["narrative_vector"].tolist() if isinstance(signals["narrative_vector"], np.ndarray) else signals["narrative_vector"],
            "tactical": "Neutral", # Placeholder for advanced tactical mismatch logic
            "narrative_arc": "RevengeArc" if signals["momentum_phase"] == "Surging" else "Standard" # Placeholder logic
        }


# ---------------------------------------------------
# MAIN WRAPPER
# ---------------------------------------------------

class RegimeEngine:
    def __init__(self):
        self.feature = FeatureBuilder()
        self.integrate = SignalIntegrator()
        self.compose = RegimeComposer()

    def process_game(
        self,
        chunk_data: List[Dict[str, Any]],
        player_history: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Main entry point.
        chunk_data: List of dicts form vector tagging output (tags + embedding)
        player_history: Dict of historical scores {'tag_scores': [...], 'health_scores': [...]}
        """

        # 1. Build Features from Raw Data
        features = self.feature.build(chunk_data)
        
        # 2. Integrate with History (Time Series)
        integrated = self.integrate.integrate(features, player_history)
        
        # 3. Compose Final Regime Object
        regime = self.compose.compose(integrated)
        
        return regime

if __name__ == "__main__":
    # Simple Test
    engine = RegimeEngine()
    
    # Mock Data
    mock_chunks = [
        {"vector_tags": {"DominantArc": "Comeback", "NarrativeIntensity": "High"}, "embedding": [0.1]*1024},
        {"vector_tags": {"EmotionalTone": "Euphoric"}, "embedding": [0.2]*1024}
    ]
    
    mock_history = {
        "tag_scores": [0.5, 0.4, 0.6, 0.7, 0.8], # Trending up
        "health_scores": [0, 0, 0]
    }
    
    print("Testing Regime Engine...")
    result = engine.process_game(mock_chunks, mock_history)
    print("Result:", result)
