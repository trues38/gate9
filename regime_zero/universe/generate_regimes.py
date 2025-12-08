import sys
import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.ingest.fetch_market_data import get_market_vector
from regime_zero.ingest.fetch_headlines import get_daily_headlines
from regime_zero.embedding.vectorizer import create_market_prompt
from utils.openrouter_client import ask_llm

OUTPUT_FILE = "regime_zero/data/regime_objects.jsonl"

def generate_regime_for_date(date_str):
    """
    Generates a Regime Object for a specific date using LLM.
    """
    print(f"📜 [Regime Zero] Generating Regime for {date_str}...")
    
    # 1. Get Data
    market_data = get_market_vector(date_str)
    headlines = get_daily_headlines(date_str)
    
    if not any(market_data.values()) and not headlines:
        print(f"⚠️ Skipping {date_str}: No data.")
        return None
        
    # 2. Create Prompt Trigger
    trigger_input = create_market_prompt(date_str, market_data, headlines)
    
    # 3. Call LLM (The Historian)
    system_prompt = """You are the AI Market Historian.
Your goal is to analyze the provided market snapshot and define a unique 'Regime Object'.
Focus on structural, causal, and narrative patterns.
Do not just summarize the news; interpret the underlying economic mechanics."""

    user_prompt = f"""
Analyze the following market snapshot and define the "Regime".

[Input Snapshot]
{trigger_input}

[Output Format - JSON Only]
{{
    "regime_name": "Creative & Descriptive Name (e.g., 'War-Stagnation', 'Tech-Led Melt-Up')",
    "signature": ["Characteristic 1", "Characteristic 2", "Characteristic 3", "Characteristic 4", "Characteristic 5"],
    "historical_vibe": "Brief description of the historical atmosphere (e.g., 'Reminiscent of late 90s irrational exuberance')",
    "structural_reasoning": "5 sentences explaining WHY this is the regime.",
    "risks": ["Risk 1", "Risk 2", "Risk 3"],
    "upside": ["Upside 1", "Upside 2", "Upside 3"],
    "date": "{date_str}"
}}
"""
    
    try:
        response = ask_llm(user_prompt, system_prompt=system_prompt)
        if not response:
            print("❌ LLM returned None.")
            return None
            
        # Clean response to ensure JSON
        # Sometimes LLMs add markdown code blocks
        clean_response = response.replace("```json", "").replace("```", "").strip()
        regime_object = json.loads(clean_response)
        
        # Ensure date is in object
        regime_object['date'] = date_str
        
        return regime_object
        
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON from LLM response: {response[:100]}...")
        return None
    except Exception as e:
        print(f"❌ Error generating regime: {e}")
        return None

def run_backfill(start_date, end_date):
    current_date = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    
    with open(OUTPUT_FILE, "a") as f:
        while current_date <= end_date_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            
            regime = generate_regime_for_date(date_str)
            if regime:
                f.write(json.dumps(regime) + "\n")
                f.flush()
                print(f"✅ Saved Regime: {regime['regime_name']}")
            
            current_date += timedelta(days=1)
            # Sleep slightly to avoid rate limits if needed
            time.sleep(1)

if __name__ == "__main__":
    # Test with last 3 days
    end = datetime.now()
    start = end - timedelta(days=2)
    run_backfill(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
