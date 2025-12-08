import os
import logging
import time
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_scenario_composer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Env
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / 'econ_pipeline' / '.env'
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration
MODEL_NAME = "openai/gpt-4o-mini" # Reliable & Cheap
TARGET_COUNTRIES = ['KR', 'US', 'JP', 'CN']

def fetch_high_signal_news(days=2):
    """Fetch top signal news from the last N days."""
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    news_data = {}
    for country in TARGET_COUNTRIES:
        try:
            response = supabase.table('global_news_all')\
                .select('title, summary, signal_score')\
                .eq('country', country)\
                .gte('published_at', start_date)\
                .order('signal_score', desc=True)\
                .limit(5)\
                .execute()
            news_data[country] = response.data
        except Exception as e:
            logger.error(f"Error fetching news for {country}: {e}")
            news_data[country] = []
            
    return news_data

def generate_scenarios(news_data):
    """Generate 3 scenarios using LLM."""
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter API Key missing.")
        return None

    # Prepare Context
    context = "Recent High-Signal News:\n"
    for country, items in news_data.items():
        context += f"\n[{country}]\n"
        for item in items:
            score = item.get('signal_score', 0)
            context += f"- (Score: {score}) {item['title']}: {item['summary']}\n"

    prompt = f"""
    You are the 'Scenario Composer' of an elite economic intelligence unit.
    Based on the following high-signal global news, generate 3 distinct future scenarios for the Global Economy (focusing on KR/US/JP/CN interactions).

    News Context:
    {context}

    Required Output Format (JSON):
    {{
        "positive_case": {{
            "title": "...",
            "description": "...",
            "probability": "0-100%"
        }},
        "neutral_case": {{
            "title": "...",
            "description": "...",
            "probability": "0-100%"
        }},
        "negative_case": {{
            "title": "...",
            "description": "...",
            "probability": "0-100%"
        }}
    }}
    
    Keep descriptions professional, insightful, and forward-looking (1 week to 1 month horizon).
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://macromind.ai",
                "X-Title": "MacroMind Orchestra",
            },
            data=json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are a strategic economic forecaster. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }),
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"LLM Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return None

def save_scenarios(scenarios_json):
    """Save scenarios to DB (Need a table for reports/scenarios)."""
    # For now, we'll just log it or save to a file/new table.
    # Let's assume we create a 'daily_scenarios' table or just log.
    # Plan didn't specify table, so I'll save to a JSON file for now.
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"scenarios_{timestamp}.json"
    with open(f"orchestra/{filename}", "w") as f:
        f.write(scenarios_json)
    logger.info(f"Saved scenarios to orchestra/{filename}")

def run_composer():
    logger.info("Agent 10 (Scenario Composer) Started.")
    
    # 1. Fetch Data
    news_data = fetch_high_signal_news()
    
    # Check if we have enough data
    total_news = sum(len(v) for v in news_data.values())
    if total_news < 5:
        logger.warning("Not enough high-signal news found. Waiting...")
        return

    # 2. Generate
    result = generate_scenarios(news_data)
    
    # 3. Save
    if result:
        save_scenarios(result)
        logger.info("Scenario generation complete.")

if __name__ == "__main__":
    # In a real loop, this might run once per day or on trigger.
    # For testing, run once.
    run_composer()
