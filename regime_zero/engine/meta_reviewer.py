import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

load_dotenv()

def run_meta_review(junior_outputs):
    print("⚖️  Meta Reviewer is analyzing the 5 reports...")
    
    # 1. Prepare Context
    context_str = ""
    for name, data in junior_outputs.items():
        if data:
            context_str += f"\n=== {name} REPORT ===\n{json.dumps(data, indent=2)}\n"
            
    # 2. Prompt
    system_prompt = """You are the 'Meta Reviewer' of Regime Zero.
Your goal is to synthesize the outputs of 5 Junior Analysts into a single, coherent Consensus Signal.

**THE ANALYSTS**:
1. Qwen (Narrative)
2. DeepSeek (Quant)
3. Grok (Risk)
4. GPT-mini (Structure)
5. Gemini (News)

**YOUR TASK**:
1. **Evaluate**: Who made the best points? Who is hallucinating?
2. **Resolve Conflicts**: If Qwen says Buy but Grok says Sell, who is right based on the data?
3. **Synthesize**: Create a JSON output that merges the best insights.

**OUTPUT FORMAT (Strict JSON)**:
{
  "model_evaluations": [
    {
      "model": "Qwen14B",
      "strength_used": ["narrative flow"],
      "weakness_trimmed": ["accuracy drift"],
      "conflict_with": ["DeepSeekV3"]
    }
  ],
  "final_consensus": {
    "equity": "Buy/Sell/Hold",
    "gold": "Buy/Sell/Hold",
    "crypto": "Buy/Sell/Hold"
  },
  "risk_factors": [
    "rates",
    "geopolitical tensions"
  ],
  "executive_summary": "One paragraph synthesis of the regime."
}
"""

    user_prompt = f"""
**JUNIOR ANALYST OUTPUTS**:
{context_str}

**INSTRUCTIONS**:
Generate the Consensus JSON.
"""

    try:
        # User requested DeepSeek V3. We try OpenRouter.
        # If unavailable, fallback to Qwen 14B (Main LLM)
        model = "deepseek/deepseek-chat"
        response = ask_llm(user_prompt, system_prompt=system_prompt, model=model)
        
        if not response:
            print("⚠️ DeepSeek failed, falling back to Qwen...")
            key = os.getenv("MAIN_LLM_KEY")
            url = os.getenv("MAIN_LLM_URL")
            if url: url = url.rstrip("/") + "/chat/completions"
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=os.getenv("MAIN_LLM_MODEL"), api_key=key, base_url=url)

        if response:
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_resp)
        else:
            return None
            
    except Exception as e:
        print(f"❌ Meta Reviewer Failed: {e}")
        return None

if __name__ == "__main__":
    # Test
    pass
