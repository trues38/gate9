import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

HISTORY_FILE = "regime_zero/data/history_vectors.jsonl"

def load_history_prompts():
    prompts = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    prompts[data['date']] = data.get('prompt_preview', '')
                except:
                    pass
    return prompts

def explain_regime_match(today_date, today_prompt, matched_regime, similarity_score):
    """
    Generates an explanation for why today matches the regime.
    """
    print(f"🧠 [Regime Zero] Explaining Match: {today_date} vs {matched_regime['name']}...")
    
    # Get a representative date from the regime
    # Ideally the one closest to centroid, but first one is fine for now
    ref_date = matched_regime['dates'][0]
    history_prompts = load_history_prompts()
    ref_prompt = history_prompts.get(ref_date, "No data available.")
    
    system_prompt = """You are the AI Macro Regime Engine. 
Your job is to explain why the current market condition is structurally similar to a historical regime.
Focus on causal links: rates, liquidity, sentiment, and sector narratives.
Be concise and professional."""

    user_prompt = f"""
Compare the following two market snapshots and explain why they belong to the same regime.

--- CURRENT MARKET ({today_date}) ---
{today_prompt}

--- HISTORICAL REGIME SAMPLE ({ref_date}) ---
{ref_prompt}

---
Similarity Score: {similarity_score:.2f}

Explain the structural similarity in 3 bullet points.
"""

    explanation = ask_llm(user_prompt, system_prompt=system_prompt)
    return explanation

if __name__ == "__main__":
    # Test
    today = "2025-12-01"
    prompt = "Market is booming. Tech stocks up. Rates stable."
    regime = {"name": "Regime 1", "dates": ["2025-11-30"]}
    
    expl = explain_regime_match(today, prompt, regime, 0.85)
    print("\n--- Explanation ---")
    print(expl)
