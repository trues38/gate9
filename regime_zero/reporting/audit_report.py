import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

load_dotenv()

def audit_report(report_path, candidates_path):
    print(f"🕵️‍♂️ Auditing Report: {report_path}...")
    
    # 1. Load Report
    with open(report_path, "r") as f:
        report_content = f.read()
        
    # 2. Load Data
    with open(candidates_path, "r") as f:
        candidates = json.load(f)
    top_5 = candidates[:5]
    
    # 3. Construct Audit Prompt
    system_prompt = """You are the 'Risk Manager' and 'Lead Editor' of Regime Zero.
Your job is to audit the reports written by the CIO (also an AI) for logical consistency and clarity.
You are critical, precise, and demand causal explanations.
"""
    
    user_prompt = f"""
**THE REPORT TO AUDIT**:
{report_content}

**THE UNDERLYING DATA (Top 5 Twins)**:
{json.dumps(top_5, indent=2)}

**USER CRITIQUE (The "Audit Findings")**:
1. **Logical Inconsistency (Gold vs Equities)**:
   - In the #1 Twin (2021-04-17), Gold was +5.5%.
   - In the Consensus (Top 5), Gold had an 80% Win Rate (same as S&P 500).
   - YET, the report concludes: "S&P 500 = Clear Buy" but "Gold = Neutral".
   - **WHY?** Is this a hallucination, or is there a subtle reason (e.g., volatility, macro context) that justifies this divergence?

2. **Vague Terminology**:
   - The report uses terms like "bifurcated" and "structural hedging".
   - The user feels these are "fancy words without clear causal meaning".
   - **Explain exactly what you meant by these terms in this specific context.**

**INSTRUCTIONS**:
Write a "Defense & Clarification" memo.
1. **Address the Gold/SPY Discrepancy**: Explain the reasoning. If it was a mistake/hallucination, admit it. If it was intentional (e.g., based on the *nature* of the other twins or the regime vibe), explain the logic deeply.
2. **Define the Terms**: Translate "bifurcated" and "structural hedging" into plain English with concrete examples from the data.
3. **Verdict**: Should the report be revised?
"""

    try:
        # Use DashScope Qwen
        qwen_key = os.getenv("MAIN_LLM_KEY")
        qwen_url = os.getenv("MAIN_LLM_URL")
        qwen_model = os.getenv("MAIN_LLM_MODEL")
        
        if qwen_key and qwen_url:
            full_url = qwen_url.rstrip("/") + "/chat/completions"
            print(f"🚀 Asking Qwen ({qwen_model}) to explain itself...")
            response = ask_llm(user_prompt, system_prompt=system_prompt, model=qwen_model, api_key=qwen_key, base_url=full_url)
            
            if response:
                print("\n" + "="*40)
                print("🧠 QWEN'S SELF-AUDIT RESPONSE")
                print("="*40 + "\n")
                print(response)
            else:
                print("❌ Failed to get response.")
        else:
             print("❌ Missing Credentials.")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        report_file = "Morning_Brief_2025-12-01.md"
        
    audit_report(report_file, "regime_zero/engine/twin_candidates.json")
