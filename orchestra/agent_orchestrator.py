import os
import logging
import json
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
try:
    import agent_antigravity
except ImportError:
    from orchestra import agent_antigravity

try:
    from auto_sql_engine.auto_sql import run_auto_sql_engine
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from auto_sql_engine.auto_sql import run_auto_sql_engine

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_orchestrator.log"),
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
    # exit(1) # Don't exit in library mode

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    logger.error("Failed to init Supabase")
    supabase = None

# Configuration
MODEL_NAME = "x-ai/grok-4.1-fast:free"
TARGET_COUNTRIES = ['US', 'CN', 'JP', 'KR']

def fetch_news_by_country(country, days=2, target_date=None):
    """Fetch high-signal news for a specific country from preprocess_daily."""
    try:
        query = supabase.table('preprocess_daily')\
            .select('date, headline_clean')\
            .eq('country', country)
            
        if target_date:
            # If target_date is provided, look for that specific date
            # We might want a small range if exact date is missing, but for now strict.
            query = query.eq('date', target_date)
        else:
            # Default to latest
            query = query.order('date', desc=True).limit(days)
            
        response = query.execute()
            
        news_items = []
        if response.data:
            for row in response.data:
                headlines = row.get('headline_clean', [])
                if isinstance(headlines, list):
                    for h in headlines:
                        # Normalize to expected format
                        news_items.append({
                            "title": h.get('title', ''),
                            "summary": h.get('summary', ''),
                            "signal_score": 0, # Preprocess might not have score per item in this list yet
                            "source": "preprocess_daily"
                        })
        return news_items[:20] # Limit to top 20 to avoid context overflow
    except Exception as e:
        logger.error(f"Error fetching news for {country}: {e}")
        return []

def analyze_country_perspective(sql_evidence, country, task_input):
    """
    Phase 2 & 3: Independent Analysis by National Persona.
    """
    if not OPENROUTER_API_KEY:
        return None

    # Define Personas
    personas = {
        "US": "US Analyst Mindset: Wall Street greed, Fed-centric, Hegemony maintenance.",
        "CN": "CN Party-Analyst Mindset: CCP Strategy, Propaganda decoding, Power dynamics.",
        "JP": "JP Conservative Macro Mindset: Yen carry trade, Inflation sensitivity, Conservative lobby.",
        "KR": "KR Tactical Analyst Mindset: Fast sentiment shifts, Supply/Demand focus, Export sensitivity."
    }
    
    persona_desc = personas.get(country, "Global Analyst")
    
    # Prepare Context from SQL Evidence
    evidence_str = json.dumps(sql_evidence, indent=2, ensure_ascii=False) if sql_evidence else "No DB Evidence."

    prompt = f"""
    You are the {persona_desc}
    
    [CRITICAL INSTRUCTION: EVIDENCE-FIRST ANALYSIS]
    1. First, analyze the [AUTO-SQL EVIDENCE] provided below. This is hard data from the database.
    2. Use this evidence to ground your analysis. Do not hallucinate data.
    3. Then, interpret the [TASK] through your specific persona lens.
    
    [TASK]
    {task_input}
    
    [AUTO-SQL EVIDENCE]
    {evidence_str}
    
    [OUTPUT FORMAT - JSON]
    {{
        "anomaly_detection": ["List specific anomalies found in the Evidence"],
        "headline_interpretation": "Interpret the evidence from your national interest perspective.",
        "micro_scenario": "Short-term prediction based on this data.",
        "cross_national_reflection": "How does this data impact your rivals/allies?"
    }}
    """
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://macromind.ai",
                "X-Title": "MacroMind Orchestrator",
            },
            data=json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are a strategic national analyst. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }),
            timeout=60
        )
        
        if response.status_code == 200:
            return json.loads(response.json()['choices'][0]['message']['content'])
        else:
            logger.error(f"LLM Error for {country}: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Analysis failed for {country}: {e}")
        return None

def synthesize_meta_packet(analyses, sql_evidence=None):
    """
    Phase 5: Create Integrated Meta-Packet.
    """
    meta_packet = {
        "US": analyses.get("US", {}),
        "CN": analyses.get("CN", {}),
        "JP": analyses.get("JP", {}),
        "KR": analyses.get("KR", {}),
        "sql_evidence": sql_evidence,
        "timestamp": datetime.utcnow().isoformat()
    }
    return meta_packet

def run_orchestra(country="KR", level="G7", mode="daily", query=None, target_date=None):
    """
    Main Entry Point for Dashboard.
    """
    logger.info(f"Orchestra Triggered: Country={country}, Level={level}, Mode={mode}, Query={query}, Date={target_date}")
    
    # 0. Auto-SQL Engine Execution
    task_description = query if query else f"Analyze market signals for {country} and global context on {target_date}"
    try:
        sql_evidence_packet = run_auto_sql_engine(task_description)
        sql_evidence = sql_evidence_packet.get("clean_evidence", {})
    except Exception as e:
        logger.error(f"Auto-SQL Engine failed: {e}")
        sql_evidence = {}

    # 1. Parallel Analysis (Multi-Brain)
    analyses = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_country = {}
        for c in TARGET_COUNTRIES:
            # Note: analyze_country_perspective currently uses SQL evidence, 
            # but if we want it to use specific date news, we might need to fetch it here.
            # For now, we rely on Auto-SQL or just the final Antigravity aggregation.
            future = executor.submit(analyze_country_perspective, sql_evidence, c, task_description)
            future_to_country[future] = c
            
        for future in concurrent.futures.as_completed(future_to_country):
            c = future_to_country[future]
            try:
                result = future.result()
                if result:
                    analyses[c] = result
            except Exception as e:
                logger.error(f"Analysis failed for {c}: {e}")

    # 3. Synthesize Meta-Packet
    meta_packet = synthesize_meta_packet(analyses, sql_evidence)
    
    # 4. Call Antigravity v3.0
    logger.info("Calling Antigravity v3.0...")
    final_output = agent_antigravity.run_antigravity_with_packet(
        meta_packet, 
        level=level, 
        query=query, 
        primary_country=country,
        target_date=target_date
    )
    
    return {
        "markdown_report": final_output.get("report_text", ""),
        "json_meta": final_output.get("json_meta", {}),
        "raw_packet": meta_packet
    }

if __name__ == "__main__":
    # Test run
    print(run_orchestra())
