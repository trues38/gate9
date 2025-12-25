
from quant_engine_v1.rdata_engine import RDataEngine
import pandas as pd

def debug_values():
    print("🚀 Initializing Engine...")
    engine = RDataEngine()
    
    # Target Game: IND vs WAS (Game ID 0022501216 from Report)
    h_team = "IND" 
    a_team = "WAS"
    date_str = "2025-12-14"
    
    print(f"🔎 Analyzing {h_team} vs {a_team} on {date_str}...")
    
    # 1. Inspect Raw Metrics
    h_stats = engine._get_latest_metrics(h_team, date_str, opp_name=a_team)
    a_stats = engine._get_latest_metrics(a_team, date_str, opp_name=h_team)
    
    print("\n[HOME STATS (IND)]")
    for k, v in h_stats.items():
        print(f"  {k}: {v}")
        
    print("\n[AWAY STATS (WAS)]")
    for k, v in a_stats.items():
        print(f"  {k}: {v}")
        
    # 2. Inspect Matchup Analysis
    analysis = engine.analyze_matchup(h_team, a_team, date_str)
    
    print("\n[ANALYSIS RESULT]")
    print(f"  Edge Score: {analysis['edge_score']}")
    print(f"  Risk Score: {analysis['risk_score']}")
    print(f"  Expected Margin: {analysis['market_analysis']['expected_margin']}")
    print(f"  Decomposition: {analysis['market_analysis']['decomposition']}")

if __name__ == "__main__":
    debug_values()
