import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

load_dotenv()

def generate_final_reports(consensus_json, date):
    print("👔 Senior CIO is writing the final reports...")
    
    # 1. Institutional Report
    inst_system_prompt = """You are the Senior CIO of Regime Zero.
Write a **Formal Institutional Investment Memorandum**.
Tone: Authoritative, Dense, Data-Driven, Professional (Goldman Sachs/Bridgewater style).
Audience: Pension Funds, Sovereign Wealth Funds.
"""
    inst_user_prompt = f"""
**CONSENSUS SIGNAL**:
{json.dumps(consensus_json, indent=2)}

**DATE**: {date}

**INSTRUCTIONS**:
Write the full Institutional Report.
Structure:
1. Executive Summary
2. Macro-Regime Analysis
3. Asset Allocation Strategy (Equities, Gold, Crypto)
4. Risk Vectors
5. Conclusion
"""

    # 2. Personal Report
    pers_system_prompt = """You are the Senior CIO of Regime Zero.
Write a **Personal Action Report**.
Tone: Direct, Concise, Action-Oriented, "No Fluff".
Audience: High Net Worth Individual (HNWI) who wants to know "What do I do today?".
"""
    pers_user_prompt = f"""
**CONSENSUS SIGNAL**:
{json.dumps(consensus_json, indent=2)}

**DATE**: {date}

**INSTRUCTIONS**:
Write the Personal Report.
Structure:
1. The Bottom Line (1 sentence)
2. The Play (Buy/Sell/Hold with sizing)
3. The "Why" (Bullet points)
4. The Trap (What to watch out for)
"""

    reports = {}
    
    try:
        # User requested GPT-4o or Sonnet. Try OpenRouter.
        model = "openai/gpt-4o"
        
        # Institutional
        print("   Writing Institutional Report...")
        inst_resp = ask_llm(inst_user_prompt, system_prompt=inst_system_prompt, model=model)
        if not inst_resp: # Fallback
             inst_resp = ask_llm(inst_user_prompt, system_prompt=inst_system_prompt, model=os.getenv("MAIN_LLM_MODEL"))
        reports['institutional'] = inst_resp
        
        # Personal
        print("   Writing Personal Report...")
        pers_resp = ask_llm(pers_user_prompt, system_prompt=pers_system_prompt, model=model)
        if not pers_resp: # Fallback
             pers_resp = ask_llm(pers_user_prompt, system_prompt=pers_system_prompt, model=os.getenv("MAIN_LLM_MODEL"))
        reports['personal'] = pers_resp
        
        return reports

    except Exception as e:
        print(f"❌ Senior CIO Failed: {e}")
        return None

if __name__ == "__main__":
    pass
