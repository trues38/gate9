import os
import sys
import json
from datetime import datetime, timedelta
from typing import List

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm

class MonthlyBuilder:
    """
    Summary Factory: Monthly Layer
    Aggregates Weekly Summaries into a Monthly Report.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
    def fetch_weekly_summaries(self, month_date: datetime, country: str) -> List[str]:
        """Fetch weekly summaries that fall within the month."""
        # Logic: Select weeks where end_date is in this month
        start_of_month = month_date.replace(day=1)
        # End of month calculation
        next_month = (start_of_month + timedelta(days=32)).replace(day=1)
        end_of_month = next_month - timedelta(days=1)
        
        try:
            res = self.supabase.table("weekly_summaries")\
                .select("summary, start_date, end_date")\
                .eq("country", country)\
                .gte("end_date", start_of_month.strftime("%Y-%m-%d"))\
                .lte("end_date", end_of_month.strftime("%Y-%m-%d"))\
                .order("start_date")\
                .execute()
            
            return [f"[{r['start_date']}~{r['end_date']}] {r['summary']}" for r in res.data]
        except Exception as e:
            print(f"   ⚠️ Failed to fetch weekly summaries: {e}")
            return []

    def build_monthly_summary(self, month_str: str, country: str) -> str:
        """
        Builds and saves a Monthly Report for the given month (YYYY-MM-01).
        """
        month_date = datetime.strptime(month_str, "%Y-%m-%d")
        
        weekly_summaries = self.fetch_weekly_summaries(month_date, country)
        
        if not weekly_summaries:
            return "No data for this month."
            
        joined_summaries = "\n\n".join(weekly_summaries)
        
        # 2. LLM Summarization
        prompt = f"""
        [TASK]
        You are a Global Macro Strategist.
        Analyze the weekly summaries for {month_date.strftime('%B %Y')} in {country}.
        
        Create a 'Monthly Macro Report' (15-20 lines).
        Focus on:
        1. Macro Regime (Inflation/Growth/Stagflation/Crisis)
        2. Structural Changes (Fed Policy, Geopolitics)
        3. Investor Psychology (Greed/Fear)
        
        [WEEKLY SUMMARIES]
        {joined_summaries}
        """
        
        try:
            summary = ask_llm(prompt, model="google/gemini-flash-1.5")
            
            # 3. Save to DB
            data = {
                "month": month_str,
                "country": country,
                "summary": summary,
                "macro_tags": json.dumps(["Regime", "Macro"])
            }
            self.supabase.table("monthly_summaries").insert(data).execute()
            print(f"   💾 Saved Monthly Summary ({month_str})")
            return summary
            
        except Exception as e:
            print(f"   ❌ Monthly Build Failed: {e}")
            return ""

if __name__ == "__main__":
    builder = MonthlyBuilder()
    builder.build_monthly_summary("2023-01-01", "US")
