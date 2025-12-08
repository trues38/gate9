import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_zero.engine.council import run_council_meeting

def test_council():
    print("🧪 Testing Council of Historians...")
    
    date_str = "2025-12-02"
    market_data = {
        "Oil": {"value": 85.0, "z_score": 1.8},
        "Dollar": {"value": 98.0, "z_score": -1.2},
        "Rates": {"value": 4.5, "z_score": 0.5}
    }
    headlines = [
        "Oil surges on supply concerns",
        "Dollar weakens despite rate hold",
        "Tech stocks rally on AI news"
    ]
    
    print("\n🏛️ Convening Council...")
    regime = run_council_meeting(date_str, market_data, headlines)
    
    if regime:
        print("\n✅ Council Consensus Reached!")
        print(json.dumps(regime, indent=2))
    else:
        print("\n❌ Council Failed.")

if __name__ == "__main__":
    test_council()
