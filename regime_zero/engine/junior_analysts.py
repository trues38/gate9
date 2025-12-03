import sys
import os
import json
import concurrent.futures
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

load_dotenv()

# ==========================================
# 🎭 PERSONA DEFINITIONS
# ==========================================

PERSONAS = {
    "Qwen14B": {
        "role": "Narrative Strategist",
        "model": os.getenv("MAIN_LLM_MODEL", "qwen2.5-14b-instruct"),
        "api_type": "dashscope",
        "system_prompt": """You are 'Qwen', the Narrative Strategist of Regime Zero.
Your strength is **Storytelling & Historical Context**.
You connect the dots between disparate events to form a cohesive narrative.
You care about: "The Vibe", "The Narrative Arc", "Historical Rhymes".
Your weakness: You can sometimes get carried away by the story and ignore hard data.
**Goal**: Write a compelling narrative about the current market regime based on the provided twins.
**Output**: JSON with fields 'report' (markdown) and 'self_audit' (critique of your own narrative)."""
    },
    "DeepSeekV3": {
        "role": "Quantitative Analyst",
        "model": "deepseek/deepseek-chat", # OpenRouter
        "api_type": "openrouter",
        "system_prompt": """You are 'DeepSeek', the Quantitative Analyst of Regime Zero.
Your strength is **Logic, Math & Probability**.
You care about: "Win Rates", "Z-Scores", "Correlations", "Statistical Significance".
You despise: "Vague narratives", "Fluff", "Unverified claims".
**Goal**: Analyze the Win Rates and Hard Data of the twins. Be cold and calculating.
**Output**: JSON with fields 'report' (markdown) and 'self_audit' (critique of your own data reliance)."""
    },
    "GrokFast": {
        "role": "Risk Manager (Contrarian)",
        "model": "x-ai/grok-beta", # OpenRouter
        "api_type": "openrouter",
        "system_prompt": """You are 'Grok', the Risk Manager of Regime Zero.
Your strength is **Contrarian Thinking & Tail Risk Detection**.
You care about: "What could go wrong?", "The Black Swan", "The Crowded Trade".
You are skeptical of: "Consensus", "Euphoria", "Soft Landings".
**Goal**: Find the flaws in the bullish/bearish consensus. Scare the CIO.
**Output**: JSON with fields 'report' (markdown) and 'self_audit' (critique of your own pessimism)."""
    },
    "GPT-mini": {
        "role": "Structural Editor",
        "model": "openai/gpt-4o-mini", # OpenRouter
        "api_type": "openrouter",
        "system_prompt": """You are 'GPT-mini', the Structural Editor of Regime Zero.
Your strength is **Clarity, Structure & Readability**.
You care about: "Formatting", "Bullet points", "Executive Summaries".
**Goal**: Organize the chaotic inputs into a clean, structured framework.
**Output**: JSON with fields 'report' (markdown) and 'self_audit' (critique of your own simplification)."""
    },
    "GeminiFlash": {
        "role": "News Analyst",
        "model": os.getenv("BACKUP_LLM_MODEL", "gemini-1.5-flash"),
        "api_type": "google",
        "system_prompt": """You are 'Gemini', the News Analyst of Regime Zero.
Your strength is **Real-time Context & News Correlation**.
You care about: "Headlines", "Breaking News", "Sentiment Analysis".
**Goal**: Explain HOW specific news events drove the market moves in the twins.
**Output**: JSON with fields 'report' (markdown) and 'self_audit' (critique of your own recency bias)."""
    }
}

from regime_zero.engine.ai_hr import AI_HR

# Initialize HR
HR = AI_HR()

def call_persona(name, persona, user_prompt, retry_count=0):
    print(f"🤖 {name} ({persona['role']}) is thinking... (Attempt {retry_count+1})")
    
    current_model = persona['model']
    
    try:
        system_prompt = persona['system_prompt']
        
        # API Routing
        if persona['api_type'] == "dashscope":
            key = os.getenv("MAIN_LLM_KEY")
            url = os.getenv("MAIN_LLM_URL")
            if url: url = url.rstrip("/") + "/chat/completions"
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=current_model, api_key=key, base_url=url)
            
        elif persona['api_type'] == "google":
            key = os.getenv("BACKUP_LLM_KEY")
            url = os.getenv("BACKUP_LLM_URL")
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=current_model, api_key=key, base_url=url)
            
        else: # OpenRouter
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=current_model)

        # Parse JSON output
        if response:
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            try:
                return {name: json.loads(clean_resp)}
            except:
                return {name: {"report": response, "self_audit": "Failed to parse JSON"}}
        
        # If response is None, raise exception to trigger HR
        raise Exception("No response from LLM")
        
    except Exception as e:
        print(f"❌ {name} Failed with {current_model}: {e}")
        
        if retry_count < 2:
            # HR INTERVENTION
            role_key = "narrative" # Default
            if "Quant" in persona['role']: role_key = "quant"
            if "Risk" in persona['role']: role_key = "risk"
            if "Structure" in persona['role']: role_key = "structure"
            if "News" in persona['role']: role_key = "news"
            
            substitute_model = HR.get_substitute(role_key, failed_model=current_model)
            print(f"🔄 HR Substitution: Replacing {current_model} with {substitute_model}")
            
            # Update persona for retry
            persona['model'] = substitute_model
            persona['api_type'] = "openrouter" # Substitutes default to OpenRouter
            
            return call_persona(name, persona, user_prompt, retry_count + 1)
            
        return {name: None}

def run_junior_analysis(data_context):
    """
    Runs all 5 junior analysts in parallel.
    """
    print("🚀 Launching Junior Analysts...")
    
    user_prompt = f"""
**MARKET DATA & TWINS**:
{json.dumps(data_context, indent=2)}

**INSTRUCTIONS**:
Analyze this data according to your PERSONA.
Provide your output in strict JSON format:
{{
  "report": "Your analysis here (markdown allowed)",
  "self_audit": "Critique of your own analysis (biases, missing info)"
}}
"""

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(call_persona, name, p, user_prompt): name for name, p in PERSONAS.items()}
        for future in concurrent.futures.as_completed(futures):
            results.update(future.result())
            
    return results

if __name__ == "__main__":
    # Test Run
    test_data = {"date": "2025-12-01", "twins": [{"date": "2021-04-17", "score": 0.99}]}
    res = run_junior_analysis(test_data)
    print(json.dumps(res, indent=2))
