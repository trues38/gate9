import sys
import os
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

OBJECTS_FILE = "regime_zero/data/regime_objects.jsonl"
FAMILIES_FILE = "regime_zero/data/regime_families.json"

def find_twin(target_date):
    print(f"🔍 Searching for Historical Twin of {target_date} (Vector Mode)...")
    
    # 1. Load Data
    regimes = {}
    if os.path.exists(OBJECTS_FILE):
        with open(OBJECTS_FILE, "r") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    regimes[r['date']] = r
                except:
                    pass
    
    if target_date not in regimes:
        print(f"❌ Target date {target_date} not found in database.")
        return

    target_regime = regimes[target_date]
    print(f"🎯 Target Regime: {target_regime['regime_name']}")
    
    # 2. Prepare Corpus
    # We will search the ENTIRE universe for the best match, not just the family.
    # But we can prioritize family members if needed. For now, global search is more impressive.
    
    dates = list(regimes.keys())
    corpus = []
    
    for d in dates:
        r = regimes[d]
        # Combine fields for rich semantic matching
        text = f"{r['regime_name']} {r['historical_vibe']} {' '.join(r['signature'])} {r.get('structural_reasoning', '')}"
        corpus.append(text)
        
    # 3. Vectorization (TF-IDF)
    # This creates a vector space based on the vocabulary of our market history
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)
    
    # Find index of target
    try:
        target_idx = dates.index(target_date)
    except ValueError:
        print("❌ Target date index error.")
        return
        
    # 4. Calculate Cosine Similarity
    # Compute similarity of target against ALL documents
    cosine_sim = cosine_similarity(tfidf_matrix[target_idx:target_idx+1], tfidf_matrix).flatten()
    
    # 5. Rank Candidates & Apply Perceptual Scaling
    # Raw cosine similarity for short text is often low (0.2-0.4).
    # We map the distribution to a "Relevance Score" (0-100%) for UI intuition.
    # Logic: The top 1% of matches in the universe are "99% Relevant".
    
    # Sort by score descending
    related_docs_indices = cosine_sim.argsort()[::-1]
    
    # Get top score and 99th percentile score to calibrate
    top_raw_score = cosine_sim[related_docs_indices[1]] # Skip self
    
    # Simple scaling: Map [0.1, top_raw_score] -> [0.5, 0.98]
    def scale_score(raw, max_raw):
        if raw <= 0.1: return raw * 5 # Noise floor
        # Logarithmic boost
        boosted = 0.5 + 0.5 * (raw / max_raw)
        return min(0.99, boosted)

    scored_candidates = []
    for idx in related_docs_indices:
        if dates[idx] == target_date:
            continue # Skip self
            
        raw_score = cosine_sim[idx]
        final_score = scale_score(raw_score, top_raw_score)
        
        scored_candidates.append((final_score, regimes[dates[idx]]))
        
        if len(scored_candidates) >= 10: # Keep top 10
            break
    
    # 6. Report Top 3
    print("\n🏆 TOP 3 HISTORICAL TWINS (Vector Similarity + Perceptual Scaling)")
    print("="*40)
    
    top_twin = scored_candidates[0][1]
    top_score = scored_candidates[0][0]
    
    for i, (score, twin) in enumerate(scored_candidates[:3]):
        print(f"\n#{i+1} Match ({score:.1%}): {twin['date']}")
        print(f"🏷  Name: {twin['regime_name']}")
        print(f"🌊 Vibe: {twin['historical_vibe']}")
        # Extract top shared keywords for display
        target_words = set(target_regime['regime_name'].lower().split())
        twin_words = set(twin['regime_name'].lower().split())
        print(f"🔑 Key Overlap: {target_words & twin_words}")

    # 7. Save for Visualization
    twin_data = {
        "source": target_date,
        "target": top_twin['date'],
        "similarity": float(top_score), # Convert numpy float to python float
        "source_name": target_regime['regime_name'],
        "target_name": top_twin['regime_name']
    }
    
    viz_path = "regime_zero/visualization/twin_data.json"
    with open(viz_path, "w") as f:
        json.dump(twin_data, f, indent=2)
    print(f"\n✨ Visualization data saved to {viz_path}")

    # 8. Save Candidates for Consensus Strategy
    candidates_data = []
    for score, twin in scored_candidates:
        candidates_data.append({
            "date": twin['date'],
            "score": float(score),
            "name": twin['regime_name'],
            "reasoning": twin.get('structural_reasoning', '')
        })
        
    cand_path = "regime_zero/engine/twin_candidates.json"
    with open(cand_path, "w") as f:
        json.dump(candidates_data, f, indent=2)
    print(f"📋 Consensus candidates saved to {cand_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "2025-12-01" # Default to latest available
        
    find_twin(target)
