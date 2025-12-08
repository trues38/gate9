import sys
import os
from typing import Dict

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.reports.report_generator import generate_daily_report

def test_product_features():
    print("🚀 Testing G9 Productization Features...")
    
    # Mock Data
    strategies = [
        {
            "ticker": "TSLA",
            "action": "SELL",
            "reason": "Geopolitical risk escalating.",
            "confidence": 0.85,
            "pattern_id": "P-028",
            "meta_rag_status": "Warning (SOFT)",
            "meta_rag_warning_document": "⚠️ Meta-RAG 경고: 과거 'Russia-Ukraine' 패턴과 유사..."
        },
        {
            "ticker": "NVDA",
            "action": "BUY",
            "reason": "AI Momentum strong.",
            "confidence": 0.90,
            "pattern_id": "P-007"
        }
    ]
    
    macro_state = {
        "regime": "NEUTRAL",
        "regime_desc": "Market is in a wait-and-see mode.",
        "VIX": {"value": 26.0} # High VIX to test Momentum impact
    }
    
    watchlist = ["TSLA", "MSFT", "NVDA", "AAPL"]
    
    print("\n[Generating Report with Watchlist...]")
    report = generate_daily_report(strategies, macro_state, watchlist)
    
    print(report)
    
    # Verification Checks
    if "G9 Market Stress Index" in report:
        print("\n✅ Sparkline Chart Detected")
    else:
        print("\n❌ Sparkline Chart Missing")
        
    if "Watchlist Analysis: Portfolio Impact" in report:
        print("✅ Watchlist Analyzer Detected")
    else:
        print("❌ Watchlist Analyzer Missing")
        
    if "[TSLA] Impact Score" in report and "Recommendation: SELL / REDUCE" in report:
        print("✅ TSLA Detailed Analysis Correct")
        
    if "Momentum: Negative (High Volatility)" in report:
        print("✅ Momentum Impact Correct")

if __name__ == "__main__":
    test_product_features()
