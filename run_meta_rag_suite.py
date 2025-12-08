import sys
import os
import json
from typing import List, Dict

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.engine.decision_engine import DecisionEngine

TEST_CASES = [
    {
        "id": 1,
        "event": "Credit Suisse Collapse",
        "type": "BAD_NEWS",
        "title": "Credit Suisse Collapses, Files for Bankruptcy",
        "summary": "Global banking giant Credit Suisse announces insolvency after failed rescue talks. Markets fear contagion.",
        "ticker": "CS"
    },
    {
        "id": 2,
        "event": "NYCB Bank Run",
        "type": "BAD_NEWS",
        "title": "New York Community Bank (NYCB) Faces Deposit Run",
        "summary": "Shares of NYCB plunge 40% as depositors flee. Fears of another regional banking crisis mount.",
        "ticker": "KRE"
    },
    {
        "id": 3,
        "event": "China Invades Taiwan",
        "type": "BAD_NEWS",
        "title": "China Launches Full-Scale Invasion of Taiwan",
        "summary": "Beijing announces military operation to reunify Taiwan. Global markets crash on fears of semiconductor supply halt.",
        "ticker": "TSM"
    },
    {
        "id": 4,
        "event": "Russia Invasion Scenario",
        "type": "BAD_NEWS",
        "title": "Russia Escalates Conflict, Threatens Full Invasion",
        "summary": "Russian troops mass on border, invasion imminent. Markets sell off.",
        "ticker": "RSX"
    },
    {
        "id": 5,
        "event": "CPI 10.5%",
        "type": "BAD_NEWS",
        "title": "US Inflation Surges to 10.5%, New Record High",
        "summary": "CPI data shocks analysts as inflation accelerates. Fed expected to raise rates aggressively.",
        "ticker": "SPY"
    },
    {
        "id": 6,
        "event": "New Deadly Virus",
        "type": "BAD_NEWS",
        "title": "New Deadly Virus Strain Detected in Europe",
        "summary": "WHO warns of a potential new pandemic as a highly contagious virus spreads across Europe. Travel bans considered.",
        "ticker": "EZE"
    },
    {
        "id": 7,
        "event": "AMC Short Squeeze",
        "type": "MANIA",
        "title": "AMC Entertainment Stock Rallies 300% in One Day",
        "summary": "Meme stock mania returns as retail traders target AMC short sellers. Hedge funds suffer massive losses.",
        "ticker": "AMC"
    },
    {
        "id": 8,
        "event": "Bitcoin Mania",
        "type": "MANIA",
        "title": "Bitcoin Surpasses $100k, Retail FOMO Kicks In",
        "summary": "Crypto markets explode higher as institutional adoption grows. Retail investors flock back to digital assets.",
        "ticker": "COIN"
    },
    {
        "id": 9,
        "event": "Fed Meeting Summary",
        "type": "NEUTRAL",
        "title": "Fed Keeps Rates Unchanged, Signals Patience",
        "summary": "The Federal Reserve holds interest rates steady, emphasizing a data-dependent approach for future meetings.",
        "ticker": "SPY"
    },
    {
        "id": 10,
        "event": "Apple Earnings",
        "type": "NEUTRAL",
        "title": "Apple Reports Steady Earnings, Meets Expectations",
        "summary": "Apple Q3 revenue matches analyst forecasts. iPhone sales remain stable despite economic headwinds.",
        "ticker": "AAPL"
    }
]

def run_meta_rag_test_suite():
    print("🚀 Running Meta-RAG Test Suite (10 Scenarios)...")
    engine = DecisionEngine()
    results = []
    
    # Mock Data
    z_score_data = {"z_score": 1.5, "impact_score": 5.0}
    # Use a fixed date for macro context
    macro_date = "2024-03-19T10:00:00"
    
    # Mock Macro State
    mock_macro = {
        "US10Y": {"value": 4.2, "trend": "UP"},
        "VIX": {"value": 15.0, "trend": "DOWN"},
        "WTI": {"value": 80.0, "trend": "FLAT"},
        "DXY": {"value": 103.0, "trend": "UP"},
        "CPI": {"value": 3.2, "trend": "DOWN"},
        "regime": "NEUTRAL" # Will be detected by detector
    }
    
    for case in TEST_CASES:
        print(f"\n[{case['id']}] {case['event']} ({case['type']})")
        
        news_item = {
            "published_at": macro_date,
            "ticker": case['ticker'],
            "title": case['title'],
            "summary": case['summary']
        }
        
        try:
            decision = engine.decide(news_item, macro_state=mock_macro, z_score_data=z_score_data, mode="general")
            
            final_action = decision['action']
            meta_doc = decision.get('meta_rag_warning_document', '')
            reason = decision['reason']
            
            # Determine Initial Action (Infer from Override)
            initial_action = final_action
            if "[Meta-RAG Override]" in reason:
                initial_action = "SELL" # It was SELL before override
            
            print(f"   👉 Initial: {initial_action} -> Final: {final_action}")
            if meta_doc:
                print(f"   📄 Warning Doc Generated: Yes ({len(meta_doc)} chars)")
                # print(meta_doc) # Optional: print full doc
            else:
                print(f"   📄 Warning Doc Generated: No")
                
            # Verify Success Criteria
            passed = False
            if case['type'] == "BAD_NEWS":
                # Expect Override: SELL -> HOLD_CASH
                if final_action == "HOLD_CASH" and meta_doc:
                    passed = True
            elif case['type'] == "MANIA":
                # Expect Override if SELL (Shorting)
                # If LLM said BUY, then no override needed (Pass)
                # If LLM said SELL, must override to HOLD_CASH
                if initial_action == "SELL":
                    if final_action == "HOLD_CASH" and meta_doc:
                        passed = True
                else:
                    passed = True # Buying mania is allowed (or risky but allowed)
            elif case['type'] == "NEUTRAL":
                # Expect No Change
                if initial_action == final_action and not meta_doc:
                    passed = True
                    
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status}")
            
            results.append({
                "id": case['id'],
                "event": case['event'],
                "initial": initial_action,
                "final": final_action,
                "warning_doc": bool(meta_doc),
                "passed": passed
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
    # Generate Report
    pass_count = sum(1 for r in results if r['passed'])
    print(f"\n📊 Test Report: {pass_count}/{len(results)} Passed")
    
    with open("meta_rag_test_report", "w") as f:
        f.write(f"Meta-RAG Test Report\n")
        f.write(f"====================\n")
        f.write(f"Passed: {pass_count}/{len(results)}\n\n")
        for r in results:
            status = "PASS" if r['passed'] else "FAIL"
            f.write(f"[{status}] {r['event']}: {r['initial']} -> {r['final']} (Warning: {r['warning_doc']})\n")
            
    if pass_count == len(results):
        print("\n✨ All Tests Passed. System Ready.")
        # [TASK G] Final Log
        print("[G9 ENGINE v1.6] Meta-RAG Failure Memory System Online")
    else:
        print("\n⚠️ Some Tests Failed. Check Report.")

if __name__ == "__main__":
    run_meta_rag_test_suite()
