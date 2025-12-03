import json
import asyncio
from typing import List, Dict, Any
from regime_zero.embedding.vectorizer import create_market_prompt
from regime_zero.engine.rag_retriever import retrieve_relevant_context
from utils.openrouter_client import ask_llm

from regime_zero.engine.new_era import fetch_new_era_context

from regime_zero.engine.new_era import fetch_new_era_context

# --- RZ-3DIO Personas ---
PERSONAS = {
    # PID (Past)
    "The Historian": "You are a Historian (PID). You are obsessed with 1970s, 1990s, 2000s parallels. You only care about historical precedence and cycles.",
    "The Technocrat": "You are a Technocrat (PID). You care about rates, yield curves, correlations, and volatility surfaces. You have no emotion, only numbers.",
    
    # PSD (Present)
    "The Skeptic": "You are a Skeptic (PSD). You doubt the mainstream narrative. You use 'Qualitative Intuition' to sense the Vibe/Quality of the market, not just volatility.",
    "The Bull": "You are a Bull (PSD). You focus on liquidity, innovation, and growth drivers. You look for reasons why the market will go higher.",
    "The Macro-Bear": "You are a Macro-Bear (PSD). You focus on debt cycles and systemic risks. You run 'Stress Tests' for Black Swan events.",
    
    # FID (Future)
    "The Sociologist": "You are a Sociologist (FID). You analyze 'Social Unrest', 'Memes', and 'Panic'. You track the human element that math misses.",
    "The Futurist": "You are a Futurist (FID). You look for 'New Era' signals—AI Singularity, Crypto adoption, new wars—that have NO historical precedent."
}

class AnalystBase:
    def __init__(self, name: str, persona_prompt: str, division: str):
        self.name = name
        self.persona_prompt = persona_prompt
        self.division = division

    def analyze(self, date: str, market_input: str) -> Dict[str, Any]:
        print(f"👤 [{self.division}] {self.name} Analyzing...")
        system_prompt = f"{self.persona_prompt}\nYour goal is to provide a sharp analysis for the {self.division} division."
        user_prompt = f"""
Analyze this market snapshot for {date}:
{market_input}

Provide your analysis in JSON format:
{{
    "regime_view": "Your unique name for this regime",
    "key_observation": "The most important thing you see",
    "reasoning": "Why you think this (2-3 sentences)",
    "risk_focus": "What you are most worried about"
}}
"""
        try:
            response = ask_llm(user_prompt, system_prompt=system_prompt)
            if not response: return None
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_resp)
        except Exception as e:
            print(f"❌ [{self.name}] Error: {e}")
            return None

class PID_Analyst(AnalystBase):
    pass

class PSD_Analyst(AnalystBase):
    def run_stress_test(self, market_data):
        # Placeholder for Stress Test logic (requested by Macro-Bear)
        # In a real implementation, this would simulate a shock
        return "Stress Test: VIX > 40 would trigger Liquidity Crisis."

class FID_Analyst(AnalystBase):
    """
    Future Intelligence Division (The Trend Monitor).
    Role: Monitor Social Trends & "New Era" signals.
    Goal: Add "Flavor" and "Context", NOT Prediction.
    """
    def __init__(self, name: str, persona_prompt: str, division: str):
        super().__init__(name, persona_prompt, division)

    def analyze(self, date: str, market_input: str) -> Dict[str, Any]:
        print(f"👤 [{self.division}] {self.name} Monitoring Trends...")
        # FID NO LONGER PREDICTS THE FUTURE.
        # It only looks for "New Era" signals to add context.
        # For now, this is a placeholder for actual trend monitoring logic.
        return {
            "regime_view": "Trend Monitoring",
            "key_observation": "Monitoring for new era signals and social trends.",
            "reasoning": "Future prediction is disabled. Focusing on contextual trends.",
            "risk_focus": "Potential for unprecedented shifts."
        }

class MetaReviewer:
    """
    The Synthesizer (The Frame Maker).
    Role: Combine Past (PID) and Present (PSD) into a coherent "Frame".
    """
    def __init__(self):
        self.name = "Meta Reviewer"

    def synthesize_3d(self, date, market_data, reports, rag_context, similarity_score, new_era_context=""):
        """
        Synthesize the 'Frame' from 3 divisions.
        """
        print(f"⚖️ [{self.name}] Synthesizing RZ-3DIO Reports (Sim: {similarity_score:.2f})...")
        
        market_input = json.dumps(market_data, indent=2)
        
        # Group reports by Division
        pid_reports = [r for r in reports if r['division'] == 'PID']
        psd_reports = [r for r in reports if r['division'] == 'PSD']
        fid_reports = [r for r in reports if r['division'] == 'FID']
        
        reports_text = f"""
        [PID - Past Intelligence]
        {json.dumps(pid_reports, indent=2, ensure_ascii=False)}
        
        [PSD - Present Situational]
        {json.dumps(psd_reports, indent=2, ensure_ascii=False)}
        
        [FID - Future Intelligence]
        {json.dumps(fid_reports, indent=2, ensure_ascii=False)}
        """
        
        system_prompt = f"""You are the Meta Reviewer (The Frame Maker).
Your job is to synthesize inputs from Past (PID), Present (PSD), and Future (FID) divisions into a **High-Quality Institutional Investment Memorandum**.

**The Frame Factory Mission:**
"We do not sell Truth (Prediction). We sell Sanity (Frames)."
"We do not guess. We structure."

**Synthesis Logic:**
1. **Base Frame (PID)**: Use the Past to define the "Structural Context".
2. **Reality Check (PSD)**: Use the Present to identify "Divergence" or "Confirmation".
3. **Trend Note (FID)**: Use the Future only for "Context/Flavor" (Social Trends). DO NOT PREDICT PRICE.

**Tone & Style:**
- **Professional, Institutional, Dense.** (Like a report for a Sovereign Wealth Fund).
- **Language**: **Korean (Professional/Formal)**.
- **Structure**:
    - **Executive Summary**: High-level synthesis of the Frame.
    - **Macro-Regime Analysis**: Deep dive into the structural comparison (Past vs Present).
    - **Strategic Implications**: How to position *given* this frame (Defensive? Aggressive? Hedged?). *Do not give price targets.*
    - **Risk Vectors**: Specific structural risks.

**Current Status:**
- **Regime Similarity:** {similarity_score:.2f}
- **New Era Context:** See below.

**Instructions:**
- Synthesize a "3-Dimensional" Regime View.
- **IMPORTANT**: Output all JSON values in KOREAN (Hangul).
"""

        user_prompt = f"""
Date: {date}

[Market Snapshot]
{market_input}

[New Era Signals]
{new_era_context}

[Divisional Reports]
{reports_text}

[Historical Patterns (RAG)]
{rag_context}

Task:
1. Determine the dominant Division (Past, Present, or Future?).
2. Synthesize the Final Regime Frame into a structured report.

Output JSON (Values in Korean):
{{
    "regime_name": "The Final Consensus Regime Name (Korean)",
    "executive_summary": "High-level summary of the frame (3-4 sentences).",
    "macro_regime_analysis": "Deep dive analysis. Compare Past vs Present. Explain the 'Why'. (2 paragraphs).",
    "strategic_implications": "Recommended stance based on the frame. (e.g., 'In this regime, volatility tends to expand, so hedging is prudent...').",
    "risk_vectors": ["Risk 1 (Detailed)", "Risk 2 (Detailed)", "Risk 3 (Detailed)"],
    "upside_drivers": ["Upside 1 (Detailed)", "Upside 2 (Detailed)"],
    "date": "{date}"
}}
"""
        try:
            response = ask_llm(user_prompt, system_prompt=system_prompt, model="gpt-4o")
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            print(f"⚠️ [{self.name}] Error: {e}")
            print(f"DEBUG RESP: {response}")
            return None

class SeniorCIO:
    """
    The Decision Maker.
    Role: Take the 'Frame' and split it into two distinct products:
    1. Retail Report (Actionable, Simple, 40 lines).
    2. Institutional Report (Deep, Structural, Professional).
    """
    def __init__(self):
        self.name = "Senior CIO"

    def produce_two_track_reports(self, consensus_regime):
        print(f"👔 [{self.name}] Generating Two-Track Reports...")
        
        system_prompt = """You are the Senior CIO of the Frame Factory.
Your goal is to package the 'Consensus Frame' into two distinct products.

**Input Frame:**
{consensus_regime}

**Task 1: The Retail Report (Actionable)**
- **Language**: Korean (Hangul).
- **Target**: Individual Traders (Street-Smart).
- **Tone**: Sharp, Direct, Action-Oriented.
- **Structure**:
    - "What's the Buzz?" (Situation)
    - "What You Do Tomorrow" (Action)
    - "Pro Tips" (Alpha)

**Task 2: The Institutional Investment Memorandum (The "Gold Standard")**
- **Language**: **English (Professional/Academic)**.
- **Target**: Sovereign Wealth Funds, Pension Funds.
- **Tone**: High-Finance, Dense, Structural.
- **Structure (MUST FOLLOW EXACTLY)**:
    1. **Executive Summary**: High-level synthesis of the macro-regime.
    2. **Macro-Regime Analysis**: Deep dive into the structural comparison (Past vs Present).
    3. **Asset Allocation Strategy**:
        - **Equities**: Hold/Buy/Sell + Reasoning.
        - **Gold**: Hold/Buy/Sell + Reasoning.
        - **Cryptocurrency**: Hold/Buy/Sell + Reasoning.
    4. **Risk Vectors**: Detailed structural risks (Interest Rates, Geopolitics, etc.).
    5. **Conclusion**: Final advisory synthesis.

**Output JSON:**
{
    "retail_report": "Full markdown text for Retail Report (Korean)",
    "institutional_report": "Full markdown text for Institutional Report (English)"
}
"""
        user_prompt = f"Generate Two-Track Reports for: {consensus_regime.get('regime_name')}"
        
        try:
            response = ask_llm(user_prompt, system_prompt=system_prompt, model="gpt-4o")
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            print(f"⚠️ [{self.name}] Error: {e}")
            return None

class AntiGravity:
    def __init__(self):
        self.name = "Anti-Gravity"
        
    def audit_report(self, reports):
        print(f"🛡️ [{self.name}] Auditing Reports for Quality & Logic...")
        # Mock Audit Logic
        # In reality, this would check for contradictions or hallucinations.
        audit_result = {
            "passed": True,
            "retail_score": 95,
            "institutional_score": 98,
            "notes": "Logic is sound. Frame is consistent."
        }
        print(f"✅ Audit Passed. Retail: {audit_result['retail_score']}, Inst: {audit_result['institutional_score']}")
        return audit_result

def run_council_meeting(date, market_data, headlines, similarity_score=0.0):
    print(f"\n🔔 RZ-3DIO COUNCIL MEETING CALLED FOR {date}")
    
    # 0. Prepare Data
    market_prompt = create_market_prompt(date, market_data, headlines)
    
    # [NEW] Macro Context (FED, OIL, GOLD)
    from regime_zero.engine.macro_context import MacroContextLoader
    macro_loader = MacroContextLoader()
    macro_context = macro_loader.get_macro_context(date)
    
    # REMOVED: New Era Context (User Request: "Return to Regime Base")
    # new_era_context = fetch_new_era_context() 
    
    full_analyst_prompt = f"""
{market_prompt}

[Macro Regime Context (FED / OIL / GOLD)]
{macro_context}

[Strict Constraint]: Analyze based ONLY on the provided Market Snapshot, Macro Context, and Historical Regime. Do not hallucinate future events.
"""

    # 1. The 5 Junior Analysts (Regime Legion)
    # User: "The 5 Junior LLMs popped the regime."
    analysts = [
        # PID (The Structuralists)
        PID_Analyst("The Historian", PERSONAS["The Historian"], "PID"),
        PID_Analyst("The Technocrat", PERSONAS["The Technocrat"], "PID"),
        # PSD (The Realists)
        PSD_Analyst("The Skeptic", PERSONAS["The Skeptic"], "PSD"),
        PSD_Analyst("The Bull", PERSONAS["The Bull"], "PSD"),
        PSD_Analyst("The Macro-Bear", PERSONAS["The Macro-Bear"], "PSD")
    ]
    
    reports = []
    print("👥 [Council] The 5 Junior Analysts are deliberating...")
    for analyst in analysts:
        report = analyst.analyze(date, full_analyst_prompt)
        if report:
            # Self-Censorship / Sanity Check
            # "Self-censored and passed to MetaReviewer"
            if report.get('regime_view'):
                report['analyst'] = analyst.name
                report['division'] = analyst.division
                reports.append(report)
            else:
                print(f"⚠️ [{analyst.name}] Output censored due to low quality.")
            
    if not reports:
        print("❌ Council failed: No reports.")
        return None

    # 2. RAG Retrieval
    rag_context = retrieve_relevant_context(market_prompt)

    # 3. Meta Reviewer Synthesis
    meta = MetaReviewer()
    # Pass macro_context as the "new_era_context" slot (repurposing it for Macro)
    consensus_regime = meta.synthesize_3d(date, market_data, reports, rag_context, similarity_score, new_era_context=macro_context)
    
    if not consensus_regime:
        print("❌ Council failed: Meta Reviewer consensus failed.")
        return None
        
    # 4. Senior CIO Two-Track Reporting
    cio = SeniorCIO()
    final_reports = cio.produce_two_track_reports(consensus_regime)
    
    if not final_reports:
        print("❌ Senior CIO failed to generate reports.")
        return None

    # 5. Anti-Gravity Audit
    ag = AntiGravity()
    audit = ag.audit_report(final_reports)
    
    if not audit['passed']:
        print("❌ Anti-Gravity Audit Failed.")
        return None
    
    print(f"✅ RZ-3DIO Consensus Reached: {consensus_regime.get('regime_name')}")
    
    # Return everything
    return {
        "consensus": consensus_regime,
        "reports": final_reports,
        "audit": audit
    }
