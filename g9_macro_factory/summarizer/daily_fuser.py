import os
import sys
from typing import List, Dict
from datetime import datetime

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm

class DailySummaryFuser:
    """
    Summary Factory: Daily Layer
    Compresses raw headlines into a structured daily summary.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
    def fetch_headlines(self, date_str: str, country: str) -> List[Dict]:
        """Fetch raw headlines for the date."""
        try:
            res = self.supabase.table("global_news_all")\
                .select("title, summary, source")\
                .eq("country", country)\
                .gte("published_at", f"{date_str}T00:00:00")\
                .lte("published_at", f"{date_str}T23:59:59")\
                .limit(250)\
                .execute()
            return res.data or []
        except Exception as e:
            # print(f"⚠️ DB Fetch Failed: {e}")
            return []

    def build_daily_context(self, date_str: str, country: str) -> str:
        """
        Compresses daily headlines into a 'Daily Context' string.
        Model: Qwen 7B (Cost-Effective)
        """
        headlines = self.fetch_headlines(date_str, country)
        
        if not headlines:
            return "No significant news reported."
            
        # Format for LLM
        text_block = "\n".join([f"- {h['title']}" for h in headlines])
        
        prompt = f"""
        [TASK]
        Summarize the following {country} market headlines for {date_str}.
        Focus on:
        1. Key Market Movers (Stocks, Sectors)
        2. Macro Events (Central Bank, Inflation, Data)
        3. Sentiment (Bullish/Bearish)
        
        Output a concise 5-10 line summary for an investor.
        
        [HEADLINES]
        {text_block}
        """
        
        try:
            # Use Gemini Flash for reliable summarization
            summary = ask_llm(prompt, model="google/gemini-flash-1.5")
            return summary
        except Exception as e:
            return f"Summarization Failed: {e}"

if __name__ == "__main__":
    fuser = DailySummaryFuser()
    print(fuser.build_daily_context("2023-01-03", "US"))
