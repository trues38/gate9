import sys
import os
import json
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.openrouter_client import ask_llm

# Define the "Employees"
EMPLOYEES = {
    "The Skeptic": "You are a cynical, sharp-tongued analyst. You believe most data is noise and 'consensus' is usually a trap. You are critical of 'black box' AI models like RAG if they just regurgitate old news.",
    "The Bull": "You are an eternal optimist but smart. You believe in innovation and paradigm shifts. You think looking at the past (RAG) misses the 'New Era' potential of things like AI.",
    "The Historian": "You respect history deeply. You believe 'this time is NOT different'. You defend RAG but admit it might fail if the context is truly unique (e.g., 2024 geopolitics + AI).",
    "The Macro-Bear": "You see systemic fragility everywhere. You worry that RAG misses the 'Black Swans' that haven't happened yet. You focus on debt and structural breaks.",
    "The Technocrat": "You care about Z-scores and correlations. If the data is an outlier (3-sigma), you don't care about narratives. You think the model should flag 'Unknown Anomalies' rather than forcing a fit.",
    "Meta Reviewer": "You are the 'Judge'. You have to weigh the evidence. You are frustrated that your 'Pattern Override' logic might be too rigid. You want to know how to be more flexible.",
    "Senior CIO": "You are the Chief Investment Officer. You care about the *Client*. You are angry that the reports are becoming 'boring' and 'robotic'. You want 'Alpha' and 'Conviction', not just data dump. You demand a solution that brings back the 'Human Edge' or 'Unique Insight'."
}

def run_town_hall():
    print("📢 [Town Hall] Calling all staff to the meeting room...")
    print("📢 [Town Hall] Topic: 'Pattern RAG is failing. It's losing our edge. How do we handle the Unprecedented?'")
    print("="*60)

    # CEO's Opening Statement (User's Clarification: Frame Factory)
    ceo_statement = """
    "오해가 있다. 다시 정리한다.
    나는 '진실을 버리고 환상을 팔자'고 한 게 아니다.
    '불가능한 예측(60% 미만)을 강요하는 구조'를 버리자는 것이다.
    
    우리의 상품은 '정답(Prediction)'이 아니라 **'관점(Frame)'**이다.
    
    1. **예측 공장이 아니라 '프레임 공장'이다**:
       - 미래를 맞추는 게 아니라, 현재 시장이 과거의 어떤 패턴(레짐) 위에 있는지 '해석하는 언어와 구조'를 제공한다.
       - 사람들은 정답이 아니라, 혼란을 정리해주는 '정리된 관점'을 산다.
    
    2. **과거 정제가 더 진실에 가깝다**:
       - 정제되지 않은 미래를 포장해서 파는 게 기만이다.
       - 과거를 완벽하게 정제해서 '깨끗한 거울'을 파는 것이야말로 진정한 가치다.
       - 로또 번호를 찍어주는 게 아니라, 로또의 확률 구조를 설명해주는 것이다.
    
    이것이 '레짐 군단'의 본질이다.
    이 방향이라면 너희의 윤리적 고민과 전문가적 자존심이 해결되는가?
    다시 묻는다. 이 '프레임 공장' 전략에 동의하는가?"
    """

    # 1. Round Table Discussion
    transcript = []
    
    # Define roles for the meeting
    MEETING_ROLES = [
        "The Technocrat", # Data Integrity
        "The Historian", # Historical Value
        "Senior CIO", # Product Value (was furious)
        "Anti-Gravity", # Ethics (was critical)
        "The Futurist", # Role definition
        "Meta Reviewer" # Synthesis
    ]
    
    if "Anti-Gravity" not in EMPLOYEES:
        EMPLOYEES["Anti-Gravity"] = "You are Anti-Gravity. You are the final gatekeeper. You are extremely rational. You worry about ethics and system stability."

    for name in MEETING_ROLES:
        persona = EMPLOYEES.get(name, "You are an analyst.")
        print(f"\n🎤 {name} is speaking...")
        
        system_prompt = f"""{persona}
        You are in the FINAL Strategic Alignment Meeting.
        The CEO has clarified the "Regime Legion" strategy.
        
        Clarification:
        - We are NOT selling lies/illusions.
        - We are selling **"Frames"** and **"Perspectives"**.
        - We focus on **Cleaning the Past** because predicting the future is impossible/deceptive.
        - Product = "Structured Language to interpret the Market".
        
        Your Task:
        1. Does this resolve your ethical/professional concerns?
        2. Do you agree with this "Frame Factory" mission?
        3. Output in KOREAN.
        """
        
        user_prompt = f"CEO Proposal: {ceo_statement}\n\nPrevious Speakers:\n" + "\n".join(transcript[-3:])
        
        try:
            response = ask_llm(user_prompt, system_prompt=system_prompt, model="gpt-4o")
            print(f"💬 {response}")
            transcript.append(f"{name}: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")

    # 2. Synthesis & Final Verdict
    print("\n" + "="*60)
    print("📝 [Meta Reviewer] Synthesizing Final Mission Statement...")
    
    synthesis_system = """You are the Meta Reviewer.
    Synthesize the Final Mission Statement based on the team's alignment.
    
    Structure:
    1. **Consensus Check**: Did the team align? (Yes/No)
    2. **The Definition**: Define "The Frame Factory" (Regime Legion).
    3. **Final Mission**: A professional, inspiring mission statement.
    
    Output in KOREAN."""
    
    synthesis_user = f"CEO Statement: {ceo_statement}\n\nTeam Discussion:\n" + "\n".join(transcript)
    
    reform_plan = ask_llm(synthesis_user, system_prompt=synthesis_system, model="gpt-4o")
    print(f"\n{reform_plan}")

if __name__ == "__main__":
    run_town_hall()
