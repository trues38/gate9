import os
import sys
import json
from typing import List, Dict
from datetime import datetime

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm

class DailyNewsFuser:
    """
    Fuses daily headlines into a coherent market briefing using country-specific LLMs.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
    def select_model(self, country: str) -> str:
        """
        Selects the optimal LLM based on country/language context.
        """
        if country in ["CN", "JP"]:
            # Qwen 2.5 14B: Best for Asian languages and local context
            return "qwen/qwen-2.5-14b-instruct"
        elif country in ["US", "KR"]:
            # Gemini 1.5 Flash: Best for long context and speed (Free Tier)
            # Fallback to GPT-4o-mini if needed
            return "google/gemini-flash-1.5"
        else:
            return "openai/gpt-4o-mini"

    def fetch_daily_news(self, date_str: str, country: str = "US") -> List[Dict]:
        """
        Fetches headlines for a specific date and country.
        """
        try:
            # Assuming table 'global_news_archive' exists
            # If not, this block will fail and catch exception, returning mock data for dry run
            res = self.supabase.table("global_news_archive")\
                .select("title, summary, source")\
                .eq("country", country)\
                .gte("published_at", f"{date_str}T00:00:00")\
                .lte("published_at", f"{date_str}T23:59:59")\
                .limit(300)\
                .execute()
                
            if res.data:
                return res.data
                
        except Exception as e:
            # print(f"⚠️ DB Fetch Failed: {e}. Using Mock Data.")
            pass
            
        # Mock Data for Dry Run / Testing
        return [
            {"title": f"Market Rally Continues in {country}", "summary": "Stocks hit new highs.", "source": "Bloomberg"},
            {"title": f"Central Bank of {country} holds rates", "summary": "No change in policy.", "source": "Reuters"},
            {"title": f"Tech sector leads gains in {country}", "summary": "AI boom drives growth.", "source": "CNBC"}
        ]

    def summarize_raw_headlines(self, news_items: List[Dict]) -> str:
        """
        Stage 1: Compress raw headlines using a cheap/fast model (Qwen 7B).
        """
        if not news_items:
            return "No news."
            
        # Use Qwen 7B for compression (Cost ~0)
        model = "qwen/qwen-2.5-7b-instruct"
        
        headlines = "\n".join([f"- {n['title']}" for n in news_items[:200]])
        
        prompt = f"""
        [TASK]
        Summarize the following headlines into a structured daily summary.
        Group by key topics.
        
        [HEADLINES]
        {headlines}
        """
        
        try:
            return ask_llm(prompt, model=model)
        except Exception as e:
            return f"Stage 1 Failed: {e}"

    def generate_regional_insight(self, summary: str, country: str) -> str:
        """
        Stage 2: Generate market insights using regional expert models.
        """
        model = self.select_model(country)
        
        prompt = f"""
        You are a Chief Market Analyst for {country}.
        Analyze the following daily summary and provide market insights.
        
        [DAILY SUMMARY]
        {summary}
        
        [OUTPUT]
        1. Market Sentiment (Bullish/Bearish/Neutral)
        2. Key Drivers
        3. Sector Impacts
        """
        
        try:
            return ask_llm(prompt, model=model)
        except Exception as e:
            return f"Stage 2 Failed: {e}"

    def fuse_news(self, news_items: List[Dict], country: str) -> str:
        """
        Orchestrates the 2-stage fusion process (Compression -> Insight).
        """
        # Stage 1: Compression
        summary = self.summarize_raw_headlines(news_items)
        
        # Stage 2: Insight
        insight = self.generate_regional_insight(summary, country)
        
        return f"[Daily Summary]\n{summary}\n\n[Market Insight]\n{insight}"

    def generate_weekly_report(self, daily_summaries: List[str]) -> str:
        """
        Aggregates daily summaries into a Weekly Trend Report.
        """
        if not daily_summaries:
            return "No data for weekly report."
            
        model = "google/gemini-flash-1.5" # Long context model
        
        joined_summaries = "\n---\n".join(daily_summaries)
        
        prompt = f"""
        You are a Macro Strategist.
        Below are the daily market summaries for the past week.
        
        [DAILY SUMMARIES]
        {joined_summaries}
        
        [TASK]
        Identify the dominant market trend for the week.
        Focus on:
        1. Direction (Uptrend/Downtrend/Choppy)
        2. Key Narrative (What drove the market?)
        3. Momentum Shift (Did sentiment change mid-week?)
        
        Output format:
        **Weekly Trend**: [Direction]
        **Narrative**: [Summary]
        """
        
        try:
            return ask_llm(prompt, model=model)
        except Exception as e:
            return f"Weekly Report Failed: {e}"

    def generate_monthly_report(self, weekly_reports: List[str]) -> str:
        """
        Aggregates weekly reports into a Monthly Macro Regime Report.
        """
        if not weekly_reports:
            return "No data for monthly report."
            
        model = "google/gemini-flash-1.5"
        
        joined_reports = "\n---\n".join(weekly_reports)
        
        prompt = f"""
        You are a Global Macro Strategist.
        Below are the weekly reports for the past month.
        
        [WEEKLY REPORTS]
        {joined_reports}
        
        [TASK]
        Determine the current Macro Regime for the month.
        Focus on:
        1. Regime (Inflationary/Deflationary/Growth/Crisis)
        2. Structural Changes (Fed Policy, Geopolitics)
        3. Risk Level (Low/Medium/High/Extreme)
        
        Output format:
        **Monthly Regime**: [Regime Name]
        **Analysis**: [Summary]
        """
        
        try:
            return ask_llm(prompt, model=model)
        except Exception as e:
            return f"Monthly Report Failed: {e}"

    def save_report(self, date_str: str, report_type: str, content: str, country: str = "US"):
        """
        Saves a generated report to the DB.
        """
        try:
            data = {
                "date": date_str,
                "type": report_type,
                "content": content,
                "country": country
            }
            self.supabase.table("g9_reports").insert(data).execute()
            # print(f"   💾 Saved {report_type} Report to DB.")
        except Exception as e:
            print(f"   ⚠️ Failed to save report: {e}")

    def fetch_latest_report(self, date_str: str, report_type: str, country: str = "US") -> str:
        """
        Fetches the most recent report BEFORE the given date (Time Machine Rule).
        """
        try:
            res = self.supabase.table("g9_reports")\
                .select("content, date")\
                .eq("type", report_type)\
                .eq("country", country)\
                .lt("date", date_str)\
                .order("date", desc=True)\
                .limit(1)\
                .execute()
                
            if res.data:
                return res.data[0]['content']
        except Exception as e:
            # print(f"   ⚠️ Failed to fetch report: {e}")
            pass
            
        return f"No {report_type} report available yet."

# Usage Example
if __name__ == "__main__":
    fuser = DailyNewsFuser()
    # Mock data test
    news = fuser.fetch_daily_news("2023-01-01", "US")
    summary = fuser.summarize_raw_headlines(news)
    print(f"Daily: {summary[:50]}...")
    
    weekly = fuser.generate_weekly_report([summary, summary, summary])
    print(f"Weekly: {weekly[:50]}...")
    
    # Test DB Save/Fetch
    # fuser.save_report("2023-01-07", "WEEKLY", weekly)
    # fetched = fuser.fetch_latest_report("2023-01-08", "WEEKLY")
    # print(f"Fetched: {fetched[:50]}...")
