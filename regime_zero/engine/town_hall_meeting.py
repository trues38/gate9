import os
from datetime import datetime
from utils.openrouter_client import ask_llm

class TownHall:
    def __init__(self):
        self.output_dir = "regime_zero/town_hall"
        self.date = datetime.now().strftime("%Y-%m-%d")
        
    def hold_meeting(self):
        print("📢 Calling Town Hall Meeting...")
        
        # Define the context
        context = """
        **Current Status:**
        1. **Objective**: Shifted to "Retail Analysis" (Service 3). Focus on "Persuasion/Narrative" over raw prediction.
        2. **Tech Stack**: 
            - Independent Regime Engines (BTC, FED, OIL, GOLD, NEWS).
            - Hybrid Aggregator (News + Price Fallback) to solve data imbalance.
            - Regime Matcher (Cross-Regime RAG) finding "Structural Twins".
        3. **Recent Win**: Successfully identified 2025-12-02 as a twin for 2025-12-03 based on "Institutional ETF + Fed Rate Cut + Oil Sanctions".
        4. **Goal**: Provide individual investors with "Actionable Wisdom" (Why/Outcome/Difference/Conclusion).
        """
        
        # Define Personas
        personas = [
            "The Architect (System Design & Stability)",
            "The Historian (Pattern Recognition & Context)",
            "The Skeptic (Risk Management & Quality Control)",
            "The Retail Advocate (User Experience & Value)"
        ]
        
        prompt = f"""
        You are simulating a strategic "Town Hall" meeting for the Regime Zero project.
        
        {context}
        
        **Task:**
        Generate a transcript of a meeting where the following personas discuss the current direction.
        Each persona should provide their honest perspective, highlighting strengths and potential risks.
        
        **Personas:**
        1. **The Architect**: Focus on the robustness of the Hybrid Aggregator and the scalability of the Regime Matcher.
        2. **The Historian**: Discuss the shift from "Correlation" to "Causal Search". Why is finding "Structural Twins" revolutionary?
        3. **The Skeptic**: Challenge the "Service 3" model. Is "Persuasion" dangerous? What if the "Outcome" data is misleading? Are we over-fitting?
        4. **The Retail Advocate**: Champion the new vision. Why do regular people need this "Narrative" more than just numbers?
        
        **Format:**
        - **Title**: Town Hall Meeting - [Date]
        - **Agenda**: Review of "Service 3" Strategy & Regime Aggregation.
        - **Transcript**: Dialogue format.
        - **Consensus**: A final summary of the group's agreement and next steps.
        
        Output in Markdown.
        """
        
        response = ask_llm(prompt, system_prompt="You are the Meeting Secretary for Regime Zero.")
        
        # Save to file
        filename = os.path.join(self.output_dir, f"{self.date}_TownHall.md")
        with open(filename, 'w') as f:
            f.write(response)
            
        print(f"✅ Town Hall Minutes saved to {filename}")
        return filename

if __name__ == "__main__":
    town_hall = TownHall()
    town_hall.hold_meeting()
