from regime_zero.engine.config import RegimeConfig

# Dummy Prompts for Sports
SPORTS_REGIME_PROMPT = """
You are a Sports Analyst AI. Analyze the recent news for {asset} on {date}.
Identify the current "Regime" (e.g., Winning Streak, Crisis, Rebuilding, Title Contender).

News Context:
{news_context}

Return JSON:
{{
    "regime_label": "String",
    "confidence": "High/Medium/Low",
    "key_factors": ["List", "of", "factors"],
    "narrative": "One sentence summary."
}}
"""

SPORTS_CONFIG = RegimeConfig(
    domain_name="sports",
    assets=["PREMIER_LEAGUE", "NBA"],
    prompts={
        "PREMIER_LEAGUE": SPORTS_REGIME_PROMPT,
        "NBA": SPORTS_REGIME_PROMPT
    },
    data_dir="regime_zero/data/sports_regimes",
    output_dir="regime_zero/data/sports_regimes",
    history_file="regime_zero/data/sports_history/unified_history.csv",
    window_days={
        "PREMIER_LEAGUE": 7,
        "NBA": 3
    }
)
