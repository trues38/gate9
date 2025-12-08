import os
import sys
import json
from datetime import datetime, timedelta
from typing import List

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm
from g9_macro_factory.summarizer.daily_fuser import DailySummaryFuser

class WeeklyBuilder:
    """
    Summary Factory: Weekly Layer
    Aggregates Daily Contexts into a Weekly Summary.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.daily_fuser = DailySummaryFuser()
        
    def build_weekly_summary(self, start_date_str: str, country: str) -> str:
        """
        Builds and saves a Weekly Summary for the week starting on start_date_str.
        """
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=6)
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # 1. Collect Daily Contexts
        daily_contexts = []
        current = start_date
        while current <= end_date:
            d_str = current.strftime("%Y-%m-%d")
            # In a real pipeline, we might fetch from a daily_summaries table if we stored them.
            # Here we generate on fly or assume fast enough.
            # For efficiency, let's generate.
            ctx = self.daily_fuser.build_daily_context(d_str, country)
            if ctx and "No significant news" not in ctx:
                daily_contexts.append(f"[{d_str}] {ctx}")
            current += timedelta(days=1)
            
        if not daily_contexts:
            return "No data for this week."
            
        joined_contexts = "\n\n".join(daily_contexts)
        
        # 2. LLM Summarization
        prompt = f"""
        [TASK]
        You are a Macro Strategist.
        Analyze the daily summaries for the week of {start_date_str} to {end_date_str} in {country}.
        
        Create a 'Weekly Market Briefing' (10-15 lines).
        Focus on:
        1. Dominant Trend (Direction & Strength)
        2. Key Narratives (What drove the market?)
        3. Risk Factors (What to watch next week?)
        
        [DAILY SUMMARIES]
        {joined_contexts}
        """
        
        try:
            summary = ask_llm(prompt, model="google/gemini-flash-1.5") # Use Flash for context window
            
            # 3. Save to DB
            data = {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "country": country,
                "summary": summary,
                "macro_tags": json.dumps(["Trend", "Macro"]) # Placeholder for now
            }
            self.supabase.table("weekly_summaries").insert(data).execute()
            print(f"   💾 Saved Weekly Summary ({start_date_str} ~ {end_date_str})")
            return summary
            
        except Exception as e:
            print(f"   ❌ Weekly Build Failed: {e}")
            return ""

if __name__ == "__main__":
    builder = WeeklyBuilder()
    builder.build_weekly_summary("2023-01-02", "US") # Mon
