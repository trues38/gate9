from regime_zero.engine.council import run_council_meeting
import json

# Mock Market Data (BTC is Flying)
mock_market_data = {
    "price": {"value": 150000, "z_score": 3.5},
    "change_24h": {"value": "+5.2%", "z_score": 2.1},
    "volume": {"value": "High", "z_score": 1.8},
    "rsi": {"value": 75, "z_score": 1.5},
    "volatility": {"value": "Expanding", "z_score": 1.2}
}

# Mock Headlines (BTC Euphoria)
mock_headlines = [
    {"title": "Bitcoin Smashes $150k Barrier, Retail FOMO Returns", "source": "CoinDesk"},
    {"title": "ETF Inflows Hit Record Highs as Institutions Buy the Dip", "source": "Cointelegraph"},
    {"title": "Michael Saylor Buys Another $1B in Bitcoin", "source": "Bitcoin.com"}
]

# Mock Macro Context (BUT Fed is Killing the Party)
# We override the MacroContextLoader by injecting this directly into the prompt via a temporary hack or just modifying the input string if we could.
# Since run_council_meeting loads it internally, we'll mock the loader or just modify run_council_meeting to accept an override.
# For this test, let's subclass or monkeypatch.

from regime_zero.engine import council
from regime_zero.engine.macro_context import MacroContextLoader

class MockMacroLoader:
    def get_macro_context(self, date):
        return """
[FED News]
- (Today) Powell: "Rates must go HIGHER to 8%. Inflation is out of control."
- (Yesterday) Fed Minutes: "Unanimous vote for aggressive tightening."

[OIL News]
- (Today) Oil Spikes to $120/barrel on Middle East War.

[GOLD News]
- (Today) Gold Crashes as Real Rates Soar.
"""

# Monkey Patch
council.MacroContextLoader = MockMacroLoader

def run_test():
    print("🧪 [Test] Running Regime Collision Scenario: 'BTC Euphoria' vs 'Macro Doom'...")
    
    result = run_council_meeting(
        date="2025-12-03", # Future date
        market_data=mock_market_data,
        headlines=mock_headlines,
        similarity_score=0.85
    )
    
    if result:
        print("\n\n🎯 [Result] Final Consensus Frame:")
        print(json.dumps(result['consensus'], indent=2, ensure_ascii=False))
        
        print("\n📜 [Institutional Report Excerpt]:")
        print(result['reports']['institutional_report'][:500] + "...")

if __name__ == "__main__":
    run_test()
