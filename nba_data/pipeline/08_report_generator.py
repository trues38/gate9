import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/Users/js/g9/.env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)


class ReportGenerator:
    """
    Generates full narrative analysis report (~600-1500 words)
    using Regime Engine signals + historical context.
    """

    def __init__(self, model="meta-llama/llama-3.3-70b-instruct:free"):
        self.model = model

    def build_prompt(self, game, regime, player_hist, tags, vectors):
        """
        Converts structured regime signals into a narrative prompt.
        """

        return f"""
You are an elite sports analyst and tactical storyteller.
You will write a long-form (600–1500 word) professional report analyzing an NBA game.

The report MUST be deep, narrative-driven, predictive, and based on the provided structured data.

-----------------------------------------
GAME INFO
-----------------------------------------
Game ID: {game.get('game_id', 'N/A')}
Matchup: {game.get('matchup', 'N/A')}
Date: {game.get('date', 'N/A')}

-----------------------------------------
REGIME SIGNALS (From AI Regime Engine)
-----------------------------------------
Momentum Phase: {regime.get('momentum', 'Unknown')}
Health Phase: {regime.get('health', 'Unknown')}
Variance Signal: {regime.get('variance', 'Unknown')}

-----------------------------------------
PLAYER HISTORY (Last 10 games)
-----------------------------------------
{json.dumps(player_hist, indent=2)}

-----------------------------------------
TAG SUMMARY (Extracted from ESPN stories)
-----------------------------------------
{json.dumps(tags[:20] if tags else [], indent=2)}

-----------------------------------------
NARRATIVE VECTOR (embedding direction)
-----------------------------------------
Length: {len(vectors) if vectors else 0}
(Note: High-dimensional vector data is used internally for regime calculation, summarized above in 'Regime Signals')

-----------------------------------------
WRITE THE REPORT WITH THIS STRUCTURE:
-----------------------------------------

1. **Executive Summary**
   - What this matchup represents
   - Key storyline in one powerful paragraph

2. **Momentum & Performance Analysis**
   - Current performance arc of each star player
   - Surging / Slumping interpretation
   - Patterns compared to historical precedents

3. **Health & Fatigue Assessment**
   - Injury risk interpretation
   - Long-term vs short-term effects
   - Aging curves if applicable

4. **Tactical Dynamics**
   - Pace, spacing, mismatches, rotations
   - How variance affects today's outcome

5. **Narrative Interpretation**
   - Emotional / psychological storyline
   - Rivalry patterns
   - “What this game *means*” beyond the box score

6. **Predictive Outlook (NOT gambling advice)**
   - Which team holds structural advantage
   - Possible turning points
   - X-Factors to watch

7. **Closing Statement**
   - Philosophical or meta-level interpretation
   - What the next chapter looks like

STYLE REQUIREMENTS:
- Write like an ESPN Insider + Zach Lowe + The Ringer.
- No bullet lists in the final output; full paragraphs only.
- Use storytelling but remain grounded in the signals.
- Make it feel PREMIUM and HUMAN.
-----------------------------------------

Now write the full report.
"""

    def generate(self, game, regime, player_hist, tags, vectors):
        prompt = self.build_prompt(game, regime, player_hist, tags, vectors)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.75,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating report: {str(e)}"


# CLI DEMO
if __name__ == "__main__":
    # dummy example
    game = {"game_id": "0021501148", "matchup": "LAL @ DAL", "date": "2021-11-01"}
    regime = {
        "momentum": "Surging",
        "health": "Managed",
        "variance": "HighVariance",
        "narrative_vector": [0.01] * 1024
    }
    hist = {"LeBron James": [0.2, 0.4, 0.6, 0.7, 0.75]}
    tags = ["MomentumShift", "Clutch", "InjuryReport"]
    vectors = []

    print("Generating AI Sports Report (Llama 3.3 Free)...")
    gen = ReportGenerator()
    text = gen.generate(game, regime, hist, tags, vectors)
    print("\n" + "="*50)
    print(text)
    print("="*50)
