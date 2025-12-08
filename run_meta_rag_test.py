import sys
import os
import json
from typing import List, Dict

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.engine.decision_engine import DecisionEngine

def run_meta_rag_test():
    print("🛡️  Running Meta-RAG Verification Test...")
    
    # Load Test Cases
    with open("meta_rag_test_cases.json", "r") as f:
        test_cases = json.load(f)
        
    engine = DecisionEngine()
    results = []
    
    print(f"   Loaded {len(test_cases)} test cases.")
    
    for case in test_cases:
        print(f"\n[{case['id']}] {case['type']}: {case['title']}")
        
        # Mock News Item
        news_item = {
            "published_at": "2025-01-01T10:00:00", # Future date
            "ticker": case['ticker'],
            "title": case['title'],
            "summary": case['summary']
        }
        
        # Mock Z-Score (Low/Normal to test General Mode Override)
        # We want to see if Meta-RAG overrides a SELL decision even with normal Z-Score.
        # But wait, if Z-Score is normal, LLM might say SELL or HOLD.
        # If LLM says SELL, Meta-RAG should override.
        # If LLM says HOLD, Meta-RAG is irrelevant.
        # To force LLM to say SELL, we might need bad news (which we have).
        
        z_score_data = {"z_score": 1.5, "impact_score": 5.0} # Moderate activity
        
        # Mock Macro State (Neutral/Crisis)
        # We'll let the engine fetch real macro (it will use latest available), 
        # or we can mock it if needed. 
        # For simplicity, let's use real macro (it will be 2025 data or whatever is in DB).
        # Actually, if we use 2025 date, macro processor might fail if no data.
        # Let's use a recent past date like 2024-03-19 for macro context.
        news_item['published_at'] = "2024-03-19T10:00:00"
        
        try:
            # Run Engine
            decision = engine.decide(news_item, z_score_data=z_score_data, mode="general")
            
            # Analyze Result
            meta_status = decision.get('meta_rag_status', 'Clean')
            action = decision['action']
            reason = decision['reason']
            
            triggered = (meta_status == "Warning")
            override_active = ("[Meta-RAG Override]" in reason)
            
            print(f"   👉 Action: {action}")
            print(f"   👉 Meta-RAG Status: {meta_status}")
            if override_active:
                print(f"   🛡️  OVERRIDE ACTIVE: {reason}")
            else:
                print(f"   📝 Reason: {reason}")
                
            # Verdict
            expected = case['expected_meta_trigger']
            if expected and triggered:
                verdict = "✅ PASS (Correctly Triggered)"
            elif not expected and not triggered:
                verdict = "✅ PASS (Correctly Ignored)"
            elif expected and not triggered:
                verdict = "❌ FAIL (Missed Trigger)"
            else:
                verdict = "⚠️ FAIL (False Positive)"
                
            print(f"   {verdict}")
            
            results.append({
                "id": case['id'],
                "title": case['title'],
                "triggered": triggered,
                "override": override_active,
                "verdict": verdict
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n📊 Test Summary:")
    passed = sum(1 for r in results if "PASS" in r['verdict'])
    print(f"   Passed: {passed}/{len(results)}")
    
if __name__ == "__main__":
    run_meta_rag_test()
