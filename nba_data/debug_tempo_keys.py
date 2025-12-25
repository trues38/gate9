from quant_engine_v1.rdata_engine import RDataEngine
import json

def test():
    rdata = RDataEngine()
    # Test with a known game (e.g., from report)
    # 2025-12-14: CLE vs CHA (0022501218)
    # Actually need team names.
    # CLE = Cleveland Cavaliers
    # CHA = Charlotte Hornets
    
    print("Running analyze_matchup...")
    analysis = rdata.analyze_matchup("Cleveland Cavaliers", "Charlotte Hornets", "2025-12-14")
    
    if analysis:
        print("Keys returned:")
        print(json.dumps(list(analysis.keys()), indent=2))
        
        print("\nChecking for Profile Keys:")
        for k in ['Pace_Sea', 'pace_sea', 'avg_diff_P_4', 'days_since_last']:
            if k in analysis:
                print(f"✅ {k}: {analysis[k]}")
            else:
                print(f"❌ {k} MISSING")
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    test()
