import os
import sys
from typing import List

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from g9_macro_factory.config import get_supabase_client

def generate_sparkline(data: List[float]) -> str:
    """
    Generates an ASCII sparkline from a list of floats.
    """
    if not data:
        return ""
        
    bars = u" ▂▃▄▅▆▇█"
    min_val = min(data)
    max_val = max(data)
    span = max_val - min_val
    
    if span == 0:
        return bars[0] * len(data)
        
    sparkline = ""
    for val in data:
        idx = int((val - min_val) / span * (len(bars) - 1))
        sparkline += bars[idx]
        
    return sparkline

def get_sparkline_data_last_30(days=30) -> List[float]:
    """
    Fetches raw impact scores for the last 30 days.
    """
    supabase = get_supabase_client()
    try:
        res = supabase.table("zscore_daily")\
            .select("impact_score")\
            .order("date", desc=True)\
            .limit(days)\
            .execute()
            
        if not res.data:
            return []
            
        scores = [r['impact_score'] for r in res.data]
        scores.reverse() # Oldest to Newest
        return scores
    except Exception as e:
        print(f"⚠️ Sparkline Data Fetch Error: {e}")
        return []

def get_market_stress_index(days=30) -> str:
    """
    Fetches last 30 days impact scores and generates a sparkline report.
    """
    scores = get_sparkline_data_last_30(days)
    
    if not scores:
        return "[No Data for Sparkline]"
        
    spark = generate_sparkline(scores)
    
    # Interpretation
    last_score = scores[-1]
    trend = "Stable"
    if last_score > 5.0: trend = "CRITICAL STRESS"
    elif last_score > 3.0: trend = "High Stress"
    elif scores[-1] > scores[0] + 2.0: trend = "Rising Stress"
    elif scores[-1] < scores[0] - 2.0: trend = "Falling Stress"
    
    return f"\n[📈 G9 Market Stress Index — 지난 {days}일 추이]\n{spark}\n(Current: {last_score:.1f} | Trend: {trend})"
