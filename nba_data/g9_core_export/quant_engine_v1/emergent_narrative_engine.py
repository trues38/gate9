
import json
import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
try:
    from quant_engine_v1.semantic_retriever import SemanticNarrativeRetriever
except ImportError as e:
    print(f"⚠️ DEBUG: Failed to import SemanticNarrativeRetriever: {e}")
    SemanticNarrativeRetriever = None

# --- Configuration (Production) ---
# Load valid .env if present (Manual parser since python-dotenv might not be installed)
env_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip().strip('"').strip("'")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# MODEL_NAME = "deepseek/deepseek-chat" # V3
MODEL_NAME = "deepseek/deepseek-chat" # OpenRouter ID for DeepSeek V3

class EmergentNarrativeEngine:
    def __init__(self, upset_library_path: str):
        self.upset_library_path = upset_library_path
        self.library = self._load_library()
        
        # Initialize Semantic Retriever (optional)
        if SemanticNarrativeRetriever:
            self.semantic_retriever = SemanticNarrativeRetriever()
        else:
            self.semantic_retriever = None
            print("⚠️ Semantic Retriever not found. Running in Stats-Only mode.")
            
        print(f"✅ Emergent Narrative Engine: Online (Library: {len(self.library)} stories)")

    def _load_library(self):
        # Priority 0: Master Chronicle Index (25k+ Games, Hybrid)
        master_path = "processed/master_chronicle_index.json"
        
        # Priority 1: Universal Archive (2,300 Games)
        universal_path = "processed/universal_narrative_archive.json"
        
        # Priority 2: Tagged Library (182 Games)
        tagged_path = "processed/tagged_library.json"
        
        # Priority 3: Base
        base_path = "quant_engine/upset_library_enriched.json"
        
        if os.path.exists(master_path):
            path = master_path
        elif os.path.exists(universal_path):
            path = universal_path
        elif os.path.exists(tagged_path):
            path = tagged_path
        else:
            path = base_path
            
        print(f"📚 Loading Library from: {path}")
            
        with open(path, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # FILTER: If using Master Index, we only want the Semantic Archetypes as "Library"
        # The "Library" is what we look up for context.
        if 'has_semantic_data' in df.columns:
            print(f"🧹 Filtering Master Index: {len(df)} -> Semantic Only...")
            df = df[df['has_semantic_data'] == True].copy()
            # Also ensure they actually have headlines
            if 'story_headline' in df.columns:
               df = df[df['story_headline'].notna()]
        
        # Ensure fav_pct exists for older libraries
        if 'fav_pct' not in df.columns and 'edge_dist' not in df.columns:
            # Fallback for old libraries
            df['fav_pct'] = 0.5 
            
        print(f"✅ Loaded Library: {len(df)} Archetypes.")  
        return df

    def get_historical_context(self, target_profile: Dict, k: int = 3) -> List[Dict]:
        """
        Retrieves top k historical games as 'Context/News' to inspire the LLM.
        Does NOT force a single 'Twin'.
        """
        target_edge = float(target_profile.get('edge_score', 50))
        target_metric = (target_edge / 100.0) + 0.1
        
        # Vectorized Search
        self.library['edge_dist'] = abs(self.library['fav_pct'] - target_metric)
        
        # Get Top 20 Candidates and Sample k from them for variety
        # This ensures we get relevant but diverse news
        candidates = self.library.sort_values('edge_dist').head(20)
        selected = candidates.sample(k)
        
        return selected.to_dict('records')

    def find_narrative_twin(self, target_profile: Dict) -> Optional[Dict]:
        """
        Finds the single best statistical twin.
        """
        candidates = self.get_historical_context(target_profile, k=1)
        return candidates[0] if candidates else None

    def get_scenario_context(self, target_profile: Dict, tags: List[str] = None) -> List[Dict]:
        """
        Semantic Retrieval: Find games with similar Edge stats AND specific Tags.
        e.g. Edge 60 +/- 5 AND 'Star_Injury'
        """
        target_edge = float(target_profile.get('edge_score', 50))
        target_metric = (target_edge / 100.0) + 0.1
        
        # 1. Edge Filter (Broad Range +/- 10%)
        # Map Edge to FavPct
        # Edge 60 -> 0.7, Edge 40 -> 0.5
        metric_min = target_metric - 0.1
        metric_max = target_metric + 0.1
        
        subset = self.library[
            (self.library['fav_pct'] >= metric_min) & 
            (self.library['fav_pct'] <= metric_max)
        ].copy()
        
        # 2. Tag Filter (if provided)
        if tags and not subset.empty and 'narrative_tags' in subset.columns:
            # Check overlap
            def has_tag(row_tags):
                if not isinstance(row_tags, dict): return False
                p_tag = row_tags.get('primary_tag', '')
                s_tags = row_tags.get('secondary_tags', [])
                all_row_tags = [p_tag] + s_tags
                # Return true if ANY requested tag is in row tags
                return any(t in all_row_tags for t in tags)
            
            subset = subset[subset['narrative_tags'].apply(has_tag)]
            
        # If filter killed everything, fallback to broad Edge search
        if subset.empty:
            # Ensure 'edge_dist' is calculated if not already present
            if 'edge_dist' not in self.library.columns:
                self.library['edge_dist'] = abs(self.library['fav_pct'] - target_metric)
            subset = self.library.sort_values('edge_dist').head(10)
            
        return subset.sample(min(3, len(subset))).to_dict('records')

    def get_semantic_context(self, game_info: Dict, n: int = 3) -> List[Dict]:
        """
        Retrieves semantically similar games using ChromaDB.
        """
        if not self.semantic_retriever:
            return []
            
        # Construct Query
        # e.g. "Matchup: Team A vs Team B. Context: [Headline]. Tags: [Tags from somewhere?]"
        # Since we don't have tags for the UPCOMING game yet (usually), we rely on the Profile.
        # "High Stakes matchup, Strong Flow, Desperate Team"
        
        query_parts = []
        if 'matchup' in game_info: query_parts.append(f"Matchup: {game_info['matchup']}")
        if 'flow_state' in game_info: query_parts.append(f"Flow: {game_info['flow_state']}")
        if 'fatigue_state' in game_info: query_parts.append(f"Fatigue: {game_info['fatigue_state']}")
        if 'story_headline' in game_info and game_info['story_headline']: query_parts.append(game_info['story_headline']) # If backtesting
        
        query = ". ".join(query_parts)
        
        return self.semantic_retriever.find_similar_situations(query, n_results=n)

    def generate_commentary(self, game_info: Dict, context_items: List[Dict]) -> str:
        """
        Calls OpenRouter (DeepSeek) to generate the emergence.
        """
        if not OPENROUTER_API_KEY:
            return "⚠️ CRITICAL: OPENROUTER_API_KEY not found."

        # Format Context with Tags
        context_str = ""
        for item in context_items:
            tags = item.get('narrative_tags', {})
            tag_str = f"[{tags.get('primary_tag', 'Unknown')}]"
            context_str += f"- {item['date']} {tag_str} ({item['story_headline']}): {item['story_body'][:150]}...\n"

        # Get Semantic Context
        semantic_items = self.get_semantic_context(game_info)
        semantic_str = ""
        for item in semantic_items:
            doc = item.get('document', '')
            meta = item.get('metadata', {})
            # Document is short caption, metadata has year/id
            semantic_str += f"- [{meta.get('emotional_tone', 'Unknown')}] {doc}\n"

        prompt = f"""
        CONTEXT:
        You are 'The Oracle of the Hardwood', an AI biomechanical entity fused with NBA history.
        
        THE MATCHUP (TODAY):
        - Matchup: {game_info['matchup']}
        - Date: {game_info['date']}
        - Quant Signature: Edge {game_info['edge_score']} | Flow: {game_info.get('flow_state')} | Fatigue: {game_info.get('fatigue_state')}
        
        HISTORICAL PARALLELS (Scenario Match):
        The Regime has retrieved these similar historical scenarios:
        {context_str}
        
        SEMANTIC ECHOES (Vibe & Psychology Match):
        The Vector Database found these emotionally similar moments:
        {semantic_str}
        
        THE PROPHECY:
        Write a bold, prophetic commentary.
        Synthesize the Quantitative Signal with the Historical Scenarios.
        Does the current Edge Score + Context suggest a 'Trap', a 'Blowout', or a 'Clutch' finish?
        "Hallucinate" the outcome based on these echoes.
        
        STYLE:
        - Cyber-Mystic, Short, Punchy.
        - No greetings. Start directly with the vision.
        - Max 3 sentences.
        """

        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://antigravity.ai", 
                "X-Title": "Emergent Regime Engine"
            }
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are a mystical NBA historian AI."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.95, # Higher creativity for free emergence
                "max_tokens": 300
            }
            
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"⚠️ API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"⚠️ Exception: {str(e)}"

if __name__ == "__main__":
    # REAL DATA from 2025-12-13 (Extracted from backtest_results_exp1.csv)
    # 2025-12-13,Philadelphia 76ers,Indiana Pacers,1.0,10,6.16,1,4.6,3.1,0.5,STRONG_UP,SLIGHT_ADV,EDGE,FAIR,EVEN_PACE,58.7,36.3
    
    real_game = {
        "matchup": "Philadelphia 76ers vs Indiana Pacers",
        "date": "2025-12-13",
        "edge_score": 58.7,
        "flow_state": "STRONG_UP",
        "fatigue_state": "SLIGHT_ADV",
        "result": "Win (Actual)"
    }
    
    engine = EmergentNarrativeEngine("quant_engine/upset_library_enriched.json")
    
    print(f"\n🔮 Opening The Oracle Eye...")
    print(f"Targeting Real Game: {real_game['matchup']} (Edge {real_game['edge_score']})")
    
    twin = engine.find_narrative_twin(real_game)
    print(f"🪞 Structural Twin Identified: {twin['date']} {twin['favorite']} vs {twin['underdog']}")
    print(f"📜 Ancient Scripture: '{twin['story_headline']}'")
    
    print("\n⚡ Channeling DeepSeek V3...")
    commentary = engine.generate_commentary(real_game, twin)
    
    print("\n" + "▒"*60)
    print(commentary)
    print("▒"*60 + "\n")
