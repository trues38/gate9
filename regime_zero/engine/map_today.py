import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.ingest.fetch_market_data import get_market_vector
from regime_zero.ingest.fetch_headlines import get_daily_headlines
from regime_zero.embedding.vectorizer import create_market_prompt
from utils.openrouter_client import ask_llm

FAMILIES_FILE = "regime_zero/data/regime_families.json"

def map_today_to_family(target_date):
    """
    Maps today's market state to the existing Regime Families.
    """
    print(f"🧭 [Regime Zero] Mapping {target_date} to Universe...")
    
    # 1. Get Data
    market_data = get_market_vector(target_date)
    headlines = get_daily_headlines(target_date)
    trigger_input = create_market_prompt(target_date, market_data, headlines)
    
    # 2. Load Families
    if not os.path.exists(FAMILIES_FILE):
        print("❌ No families file found.")
        return None
        
    with open(FAMILIES_FILE, "r") as f:
        families = json.load(f)
        
    family_descriptions = ""
    for i, fam in enumerate(families):
        family_descriptions += f"{i+1}. {fam['family_name']}: {fam['description']}\n"
        
    # 3. Call LLM (The Analyst)
    system_prompt = """You are the AI Market Analyst.
Your job is to map the current market snapshot to the most similar historical 'Regime Family'.
Analyze the structural similarities."""

    user_prompt = f"""
[Current Market Snapshot]
{trigger_input}

[Available Regime Families]
{family_descriptions}

Which Family does today belong to?
Rank the Top 3 (or fewer if less exist).

[Output Format - JSON Only]
{{
    "rankings": [
        {{"family_name": "Name", "similarity_score": 0.85, "reason": "Why..."}},
        ...
    ]
}}
"""

    try:
        response = ask_llm(user_prompt, system_prompt=system_prompt)
        if not response:
            return None
            
        clean_response = response.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_response)
        
        print("✅ Mapping Complete.")
        for rank in result['rankings']:
            print(f"- {rank['family_name']} ({rank['similarity_score']:.0%}): {rank['reason']}")
            
        return result
        
    except Exception as e:
        print(f"❌ Error mapping today: {e}")
        return None

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    map_today_to_family(today)
