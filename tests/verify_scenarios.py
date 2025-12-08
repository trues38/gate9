import sys
import os
import json
from typing import Dict, Any

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g9_macro_factory.engine.decision_engine import DecisionEngine

def run_scenarios():
    print("🧪 Starting G9 Engine Logic Verification...")
    engine = DecisionEngine()
    
    # Base News Item (Context)
    news_item = {
        "published_at": "2024-05-15T10:00:00",
        "ticker": "SPY",
        "title": "Market Crashes as Inflation Spikes",
        "summary": "Investors panic as CPI hits new highs, fearing aggressive Fed hikes."
    }
    
    print("\n--------------------------------------------------")
    print("🔹 SCENARIO 1: Real Data Check (2024-05-15)")
    print("   - Expectation: Low Z-Score (~1.02) -> SKIP (Noise Filter)")
    # Pass None to force auto-fetch
    res1 = engine.decide(news_item, macro_state=None, z_score_data=None)
    print(f"   👉 Result: {res1['action']} (Reason: {res1['reason']})")
    print(f"   👉 Z-Score: {res1.get('z_score')} | Regime: {res1.get('regime')}")
    
    
    print("\n--------------------------------------------------")
    print("🔹 SCENARIO 2: Contrarian Trigger Test (Injection)")
    print("   - Input: Z-Score = 4.5 (Extreme), Regime = INFLATION_FEAR (Real)")
    print("   - Expectation: SELL signal reversed to BUY_THE_DIP")
    
    # Inject High Z-Score
    mock_z_high = {"z_score": 4.5, "impact_score": 25.0}
    
    # We let it fetch real macro (INFLATION_FEAR)
    res2 = engine.decide(news_item, macro_state=None, z_score_data=mock_z_high)
    print(f"   👉 Result: {res2['action']} (Reason: {res2['reason']})")
    print(f"   👉 Z-Score: {res2.get('z_score')} | Regime: {res2.get('regime')}")


    print("\n--------------------------------------------------")
    print("🔹 SCENARIO 3: Safety Lock Test (Injection)")
    print("   - Input: Z-Score = 4.5, Regime = STAGFLATION (Mock)")
    print("   - Expectation: HOLD_CASH (Safety Lock Triggered)")
    
    # Inject Stagflation Macro
    mock_macro_stag = {
        "CPI": 4.5, "US10Y": 4.5, "VIX": 20.0, "DXY": 102.0, "WTI": 90.0,
        "SPY_TREND": "DOWN", # Key for Stagflation
        "KR_WON": 1300, "JPY": 140, "CN_PMI": 48
    }
    
    res3 = engine.decide(news_item, macro_state=mock_macro_stag, z_score_data=mock_z_high)
    print(f"   👉 Result: {res3['action']} (Reason: {res3['reason']})")
    print(f"   👉 Z-Score: {res3.get('z_score')} | Regime: {res3.get('regime')} | Pattern: {res3.get('pattern')}")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    run_scenarios()
