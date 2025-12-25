import sys
import os

# Ensure we can import from local quant_engine_v1
sys.path.append(os.getcwd())

from quant_engine_v1.cache_engine import CacheFusionEngine

def test_weights():
    engine = CacheFusionEngine()
    
    # Use Knicks (18) vs Magic (19)
    # 1. Standard Date (December)
    res_dec = engine.analyze_matchup("18", "19", "2025-12-14")
    
    # 2. Regime Date (June - Finals Gloom)
    res_jun = engine.analyze_matchup("18", "19", "2025-06-15")
    
    print("\n⚖️ Regime Weight Verification (Knicks vs Magic)\n")
    
    print(f"1. December 14 (Standard):")
    if res_dec:
        print(f"   - Edge Score: {res_dec['edge_score']:.1f}")
        print(f"   - Risk Score: {res_dec['risk_score']:.1f}")
    else:
        print("   - Data Missing")
        
    print(f"\n2. June 15 (Regime Active: -8.4% Impact):")
    if res_jun:
        print(f"   - Edge Score: {res_jun['edge_score']:.1f}")
        print(f"   - Risk Score: {res_jun['risk_score']:.1f}")
        
    if res_dec and res_jun:
        delta = res_jun['edge_score'] - res_dec['edge_score']
        print(f"\n📉 Impact Delta: {delta:.1f} (Expected ~ -8.4)")
        
        if abs(delta + 8.4) < 1.0:
            print("✅ VERIFIED: Regime Weights are controlling the engine.")
        else:
            print("❌ FAILURE: Weights did not apply as expected.")

if __name__ == "__main__":
    test_weights()
