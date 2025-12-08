import sys
import os
import json
from typing import Dict

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.reports.report_generator import generate_daily_report
from g9_macro_factory.engine.explainer.risk_explainer import generate_risk_explanation
from g9_macro_factory.engine.risk.unified_risk_score import calculate_unified_risk

def test_risk_features():
    print("🚀 Testing G9 Risk Features...")
    
    # Mock Data
    macro_state = {
        "regime": "STAGFLATION",
        "regime_desc": "High Inflation + Low Growth.",
        "VIX": {"value": 25.0}
    }
    
    meta_rag_warning = {
        "override_level": "HARD",
        "origin_pattern_id": "P-009",
        "fail_reason": json.dumps({
            "fail_type": "false_sell",
            "recurrence_count": 3,
            "risk_weight": 1.8,
            "impact": 5.5
        })
    }
    
    # 1. Test Unified Risk Score
    print("\n[Testing Unified Risk Score]")
    risk_score = calculate_unified_risk(macro_state, "P-009", meta_rag_warning)
    print(f"Score: {risk_score['score']} ({risk_score['label']})")
    print(f"Details: {risk_score['details']}")
    
    if risk_score['score'] > 70:
        print("✅ High Risk Correctly Identified")
    else:
        print("❌ Risk Score Too Low")
        
    # 2. Test Risk Explainer
    print("\n[Testing Risk Explainer]")
    explanation = generate_risk_explanation(meta_rag_warning, "SELL", "HOLD_CASH")
    print(explanation)
    
    if "Override: HARD" in explanation and "시스템 조치: SELL → HOLD_CASH" in explanation:
        print("✅ Explanation Format Correct")
    else:
        print("❌ Explanation Format Incorrect")
        
    # 3. Test Report Integration
    print("\n[Testing Report Integration]")
    strategies = [
        {
            "ticker": "SPY",
            "action": "HOLD_CASH",
            "reason": "Risk too high.",
            "confidence": 1.0,
            "meta_rag_status": "Warning (HARD)",
            "meta_rag_warning_document": "Raw Warning Doc...",
            "unified_risk": risk_score,
            "risk_explanation": explanation
        }
    ]
    
    report = generate_daily_report(strategies, macro_state)
    print(report)
    
    if "Unified Risk Score" in report and "📌 G9 Risk Notice" in report:
        print("\n✅ Report Integration Verified")
    else:
        print("\n❌ Report Integration Failed")

if __name__ == "__main__":
    test_risk_features()
