import sys
import os
import json
import random
from collections import Counter

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

INPUT_FILE = "regime_zero/data/regime_objects.jsonl"
OUTPUT_FILE = "regime_zero/data/regime_families.json"

def cluster_families():
    """
    Uses LLM to define families from a sample, then assigns all regimes to them.
    """
    print("🌌 [Regime Zero] Clustering 20,000+ Regimes into Families...")
    
    regimes = []
    if not os.path.exists(INPUT_FILE):
        print(f"❌ No regime objects found at {INPUT_FILE}")
        return
        
    with open(INPUT_FILE, "r") as f:
        for line in f:
            try:
                regimes.append(json.loads(line))
            except:
                pass
                
    if not regimes:
        print("❌ No regimes to cluster.")
        return
        
    print(f"📊 Total Regimes: {len(regimes)}")
    
    # 1. Sampling for Definition (Take 300 random samples)
    sample_size = min(len(regimes), 300)
    samples = random.sample(regimes, sample_size)
    
    regime_summaries = ""
    for r in samples:
        regime_summaries += f"- {r['regime_name']}: {', '.join(r['signature'][:2])}\n"
        
    print(f"🧠 Asking LLM to define families based on {sample_size} samples...")
    
    system_prompt = """You are the AI Market Architect.
Your goal is to organize a massive list of historical market regimes into coherent 'Regime Families'.
Create 10-15 distinct families that cover broad economic themes (Inflation, Tech, Crisis, Goldilocks, War, etc.).
Provide a set of 'keywords' for each family to help classify other regimes."""

    user_prompt = f"""
Here is a random sample of market regimes from history:

{regime_summaries}

Define 10-15 "Regime Families" that best categorize these and potential others.

[Output Format - JSON Only]
[
    {{
        "family_name": "Name (e.g., 'Stagflation Crisis')",
        "description": "Description...",
        "keywords": ["inflation", "stagnation", "oil", "shock", "crisis"]
    }},
    ...
]
"""

    try:
        response = ask_llm(user_prompt, system_prompt=system_prompt)
        if not response:
            print("❌ LLM returned None.")
            return
            
        clean_response = response.replace("```json", "").replace("```", "").strip()
        families = json.loads(clean_response)
        print(f"✅ Defined {len(families)} Regime Families.")
        
        # 2. Assign All Regimes to Families (Keyword Matching)
        print("🗂 Assigning all 20,000+ regimes to families...")
        
        # Initialize member_dates
        for fam in families:
            fam['member_dates'] = []
            
        # Precompute lowercase keywords
        for fam in families:
            fam['_keywords_set'] = set(k.lower() for k in fam['keywords'])
            fam['_name_lower'] = fam['family_name'].lower()
            
        unassigned_count = 0
        
        for r in regimes:
            best_fam = None
            max_score = -1
            
            # Text to match against: Name + Signature
            text = (r['regime_name'] + " " + " ".join(r['signature'])).lower()
            
            for fam in families:
                score = 0
                # Keyword match
                for k in fam['_keywords_set']:
                    if k in text:
                        score += 1
                
                # Name match bonus
                if fam['_name_lower'] in text:
                    score += 3
                    
                if score > max_score:
                    max_score = score
                    best_fam = fam
            
            if best_fam and max_score > 0:
                best_fam['member_dates'].append(r['date'])
            else:
                # Fallback: Random or "Unclassified"
                # Let's assign to "Unclassified" or just the largest generic one?
                # For viz, let's just pick the first one if score is 0 to avoid orphans, 
                # or create an "Unclassified" family.
                unassigned_count += 1
                # Assign to random family to keep viz full? No, let's be honest.
                # Actually, let's force assign to the one with best semantic overlap if we had embeddings.
                # Since we don't, let's dump into "Unclassified".
                pass

        # Clean up temp keys
        for fam in families:
            del fam['_keywords_set']
            del fam['_name_lower']
            
        print(f"✅ Assignment Complete. Unassigned: {unassigned_count}")
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(families, f, indent=2)
            
        for fam in families:
            print(f"- {fam['family_name']}: {len(fam['member_dates'])} members")
            
    except Exception as e:
        print(f"❌ Error clustering families: {e}")

if __name__ == "__main__":
    cluster_families()
