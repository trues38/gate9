import sys
import os
import json

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.reports.engine_report import generate_g9_daily_report

def test_engine_report():
    print("🚀 Testing G9 Report Renderer...")
    
    # Mock Data
    macro_state = {
        "regime": "STAGFLATION",
        "VIX": {"value": 28.5},
        "US10Y": {"value": 4.2}
    }
    
    decisions = [
        {
            "ticker": "SPY",
            "action": "HOLD_CASH",
            "confidence": 1.0,
            "pattern": "P-009",
            "reason": "Leverage Crisis detected | Risk too high.",
            "meta_rag_status": "Warning (HARD)",
            "risk_explanation": "[📌 G9 Risk Notice]\n- Override: HARD\n- Cause: P-009 Recurrence",
            "unified_risk": {
                "score": 85.0,
                "label": "High Risk"
            }
        },
        {
            "ticker": "NVDA",
            "action": "BUY",
            "confidence": 0.9,
            "pattern": "P-007",
            "reason": "AI Boom.",
            "unified_risk": {
                "score": 85.0,
                "label": "High Risk"
            }
        }
    ]
    
    watchlist = ["SPY", "NVDA", "TSLA"]
    
    print("\n[Generating Report...]")
    report = generate_g9_daily_report(macro_state, [], decisions, watchlist)
    
    print(report)
    
    # Verification
    if "# 🧠 G9 ENGINE INTELLIGENCE REPORT" in report:
        print("\n✅ Header Detected")
    if "🛡️ Unified Risk Score" in report:
        print("✅ Risk Score Detected")
    if "## 💼 Watchlist Analyzer" in report:
        print("✅ Watchlist Section Detected")
    if "[✓ Report Renderer Complete]" in report:
        print("✅ Completion Marker Detected")

if __name__ == "__main__":
    test_engine_report()
