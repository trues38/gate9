from quant_engine_v1.cache_engine import CacheFusionEngine
import json

def test():
    print("🚀 Debugging Cache Engine...")
    engine = CacheFusionEngine()
    
    # CHA vs CLE (Tomorrow)
    # IDs from my map:
    # CHA: 1610612766
    # CLE: 1610612739
    
    home_id = 1610612739 # CLE
    away_id = 1610612766 # CHA
    date = "2025-12-14"
    
    print(f"Analyzing {home_id} vs {away_id} on {date}...")
    
    res = engine.analyze_matchup(home_id, away_id, date, odds="-11.5")
    
    print("\n--- Result ---")
    print(json.dumps(res, indent=2))
    
    if res is None:
        print("❌ Result is None. Check logs above.")
    else:
        print(f"✅ Edge Score: {res.get('edge_score')}")

if __name__ == "__main__":
    test()
