import os
import sys
import json
from datetime import datetime

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g9_macro_factory.engine.decision_engine import engine

def run_test():
    print("🚀 Starting G9 Engine v1.5 Test (10 Headlines)...")
    
    # 1. Mock Data (Macro State) - REMOVED (Will be auto-fetched)
    macro_state = None
    
    # 2. Mock Z-Score (High Impact) - REMOVED (Will be auto-fetched)
    z_score_data = None
    
    # 3. Test Headlines (10 Samples)
    # Using 2024-05-15 as it has data in zscore_daily.csv
    headlines = [
        {"published_at": "2024-05-15T10:00:00", "ticker": "SPY", "title": "US CPI Rises 3.4%, Beating Expectations", "summary": "Inflation remains sticky, dampening hopes for early rate cuts."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "US10Y", "title": "Fed Chair Powell Signals 'Higher for Longer' Rates", "summary": "Powell emphasizes the need to combat inflation, sending yields higher."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "WTI", "title": "Oil Prices Surge Past $90 Amid Middle East Tensions", "summary": "Geopolitical risks escalate, threatening global energy supply."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "QQQ", "title": "Tech Stocks Tumble as Bond Yields Hit 15-Year High", "summary": "Nasdaq drops 2% as 10-year Treasury yield breaches 4.5%."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "JPY", "title": "Japan Intervenes to Support Yen as Currency Falls", "summary": "BOJ steps in after Yen hits 155 against the dollar."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "CN_PMI", "title": "China Manufacturing PMI Contracts for 5th Month", "summary": "Factory activity shrinks, signaling deepening economic slowdown."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "EUR", "title": "ECB Hikes Rates to Record High, Signals Pause", "summary": "European Central Bank raises rates to fight inflation but hints at peak."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "GS", "title": "Goldman Sachs Cuts US GDP Forecast", "summary": "Bank cites rising borrowing costs and consumer fatigue."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "BTC", "title": "Bitcoin Crashes 10% on Regulatory Crackdown Fears", "summary": "SEC lawsuit against major exchanges triggers crypto sell-off."},
        {"published_at": "2024-05-15T10:00:00", "ticker": "NVDA", "title": "NVIDIA Earnings Beat Estimates, AI Boom Continues", "summary": "Revenue doubles year-over-year, driving AI sector rally."}
    ]
    
    print(f"\n📊 Macro Context: Auto-Fetching...")
    print(f"📉 Z-Score Context: Auto-Fetching...\n")
    
    results = []
    
    for i, item in enumerate(headlines):
        print(f"[{i+1}] Analyzing: {item['title']}...")
        try:
            decision = engine.decide(item, macro_state, z_score_data)
            results.append({
                "headline": item['title'],
                "decision": decision
            })
            print(f"    👉 Action: {decision['action']}")
            print(f"    👉 Regime: {decision['regime']}")
            print(f"    👉 Pattern: {decision['pattern']}")
            print(f"    👉 Reason: {decision['reason'][:100]}...")
            print("-" * 50)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            
    # Save results for UI
    with open("g9_v1_5_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n✅ Test Complete. Results saved to g9_v1_5_test_results.json")

if __name__ == "__main__":
    run_test()
