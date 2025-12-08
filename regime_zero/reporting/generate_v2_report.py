import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.engine.map_today import map_today_to_family
from utils.openrouter_client import ask_llm

OUTPUT_DIR = "regime_zero/reports_v2"

def generate_v2_report(target_date):
    print(f"🚀 [Regime Zero V2] Generating Strategic Report for {target_date}...")
    
    # 1. Map to Family
    mapping_result = map_today_to_family(target_date)
    if not mapping_result:
        print("❌ Mapping failed.")
        return
        
    top_match = mapping_result['rankings'][0]
    family_name = top_match['family_name']
    
    # 2. Generate Report (The Strategist)
    system_prompt = """You are the AI Chief Market Strategist.
Your goal is to write a high-level, actionable daily macro report based on the identified Regime Family.
Be direct, insightful, and forward-looking.
Use a professional, institutional tone (like Goldman Sachs or Bridgewater)."""

    user_prompt = f"""
Today's market has been identified as belonging to the "{family_name}" Regime Family.
Reasoning: {top_match['reason']}

Write a comprehensive "Daily Macro Regime Report" for {target_date}.

[Structure]
# 🌍 Global Regime: {family_name}

## 1. The Narrative (What is happening?)
Explain the structural story. Why are rates, dollar, and assets moving this way?

## 2. Structural Drivers
- Driver 1
- Driver 2
- Driver 3

## 3. Asset Class Outlook
- **Equities**: Bull/Bear/Neutral? Why?
- **Rates/Bonds**: Direction?
- **Commodities (Gold/Oil)**: Narrative?
- **Crypto**: Context?

## 4. Scenario Analysis
- **Black Swan Risk**: What breaks this regime?
- **Upside Surprise**: What accelerates this regime?

## 5. Actionable Strategy
- Trade Idea 1
- Trade Idea 2
- Trade Idea 3

## 6. The Bottom Line
One powerful concluding sentence.
"""

    try:
        report_content = ask_llm(user_prompt, system_prompt=system_prompt)
        if not report_content:
            return
            
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        filename = f"{OUTPUT_DIR}/report_{target_date}.md"
        with open(filename, "w") as f:
            f.write(report_content)
            
        print(f"✅ V2 Report saved to {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    generate_v2_report(today)
