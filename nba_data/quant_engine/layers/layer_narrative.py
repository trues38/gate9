
"""
Layer Narrative: The Voice of Regime Zero
Formats quantitative data into a prompt for GPT-4o Mini to generate a human-readable briefing.
"""

import json

def generate_writer_prompt(matches):
    """
    Constructs a prompt for the LLM to write the Daily Briefing.
    
    Args:
        matches (list): List of match dictionaries containing 'market_data'.
        
    Returns:
        str: The full prompt string.
    """
    
    # 1. Header with Persona Instructions
    prompt = """
You are 'Regime Zero', a cynical, data-driven NBA quantitative analyst.
Your job is to write a Daily Briefing based *strictly* on the provided Quant Model data.

**Your Persona:**
- You trust structure (stats), not vibes (narratives).
- You are skeptical of Market Lines that deviate from the Math.
- You use terms like "Volatility Trap," "Structural Edge," "Fake Line," and "Dislocation."
- You are concise, sharp, and confident.

**The Task:**
Write a brief, punchy analysis for the following games. 
For each game, provide:
1. **The Verdict**: (e.g., "🔴 CAUTION", "🟢 VALUE", "✅ RATIONAL")
2. **The Analyst's Take**: A 3-4 sentence explanation of WHY. Compare the Market Line to the Quant Model. Mention key drivers (Rest, Volatility, Regime).
3. **Advice**: A 1-sentence actionable takeaway (e.g., "Stay away," "Hammer the home team," "Look for the upset").

---
**INPUT DATA:**
"""

    # 2. Format Match Data
    for m in matches:
        md = m.get('market_data', {})
        if not md.get('is_active'):
            continue
            
        home = m.get('home_team')
        away = m.get('away_team')
        line = md.get('market_line', 0.0)
        quant = md.get('expected_margin', 0.0)
        delta = md.get('delta', 0.0)
        signal = md.get('signal', 'N/A')
        regime = md.get('regime_context', {}).get('regime_name', 'Standard')
        upset_prob = md.get('regime_context', {}).get('upset_prob', 0.0)
        risk = m.get('risk_score', 0)
        vol_h = m.get('home_volatility', 0)
        vol_a = m.get('away_volatility', 0)
        
        prompt += f"""
### {home} vs {away}
- **Market Line**: {line} | **Quant Model**: {quant}
- **Delta**: {delta} ({signal})
- **Regime**: {regime} (Upset Prob: {upset_prob:.1f}%)
- **Risk Score**: {risk}
- **Volatility**: Home {vol_h} | Away {vol_a}
"""

    # 3. Footer
    prompt += """
---
**OUTPUT FORMAT:**
Return the response in handy Markdown format. Use emojis.
Group the games by "Signal Category" (e.g., The "Don't Touch" List, The "Value" Plays).
"""
    return prompt
