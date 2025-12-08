import os
import sys
from typing import Dict, List
from datetime import datetime

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from g9_macro_factory.summarizer.daily_fuser import DailySummaryFuser

class ContextLoader:
    """
    The Time Machine: Fetches historical context without future leakage.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.daily_fuser = DailySummaryFuser()
        
    def get_multi_timeframe_context(self, target_date_str: str, country: str = "US") -> Dict:
        """
        Fetches Monthly, Weekly, and Daily context for the target date.
        """
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        
        # 1. Monthly Context (Layer 1)
        # Rule: month < target_date's month
        first_day_of_month = target_date.replace(day=1)
        
        monthly_summary = "N/A"
        try:
            res = self.supabase.table("monthly_summaries")\
                .select("summary, month")\
                .eq("country", country)\
                .lt("month", first_day_of_month.strftime("%Y-%m-%d"))\
                .order("month", desc=True)\
                .limit(1)\
                .execute()
            if res.data:
                monthly_summary = f"[{res.data[0]['month']}] {res.data[0]['summary']}"
        except Exception as e:
            # print(f"Context Load Error (Monthly): {e}")
            pass
            
        # 2. Weekly Context (Layer 2)
        # Rule: end_date < target_date
        weekly_summaries_list = []
        try:
            res = self.supabase.table("weekly_summaries")\
                .select("summary, start_date, end_date")\
                .eq("country", country)\
                .lt("end_date", target_date_str)\
                .order("end_date", desc=True)\
                .limit(3)\
                .execute()
            
            for r in res.data:
                weekly_summaries_list.append(f"[{r['start_date']}~{r['end_date']}] {r['summary']}")
        except Exception as e:
            # print(f"Context Load Error (Weekly): {e}")
            pass
            
        weekly_context = "\n".join(weekly_summaries_list) if weekly_summaries_list else "N/A"
        
        # 3. Daily Context (Layer 3)
        # Generate on fly or fetch
        daily_context = self.daily_fuser.build_daily_context(target_date_str, country)
        
        return {
            "monthly_summary": monthly_summary,
            "weekly_context": weekly_context,
            "daily_context": daily_context
        }

if __name__ == "__main__":
    loader = ContextLoader()
    ctx = loader.get_multi_timeframe_context("2023-01-15", "US")
    print("Monthly:", ctx['monthly_summary'][:50])
    print("Weekly:", ctx['weekly_context'][:50])
    print("Daily:", ctx['daily_context'][:50])
