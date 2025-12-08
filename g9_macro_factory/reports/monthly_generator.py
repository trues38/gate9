import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List
import calendar

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm
from g9_macro_factory.prompts import DEEPSEEK_SYSTEM_PROMPT, MONTHLY_REPORT_PROMPT

class MonthlyReportGenerator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.model = "x-ai/grok-4.1-fast:free" # Grok 4.1 Fast

    def generate(self, start_date: str, end_date: str, country: str = "US"):
        print(f"   📅 Generating Monthly Report for {start_date} to {end_date} ({country})...")
        
        # 1. Fetch Daily Reports (Date-Based Aggregation)
        # Directive: "Monthly report: Filter daily reports by date to create"
        daily_reports = self._fetch_daily_reports(start_date, end_date, country)
        if not daily_reports:
            print(f"   ⚠️ No daily reports found for {start_date} to {end_date}. Skipping.")
            return None
            
        # 2. Prepare JSONs
        daily_jsons = []
        for r in daily_reports:
            try:
                if isinstance(r['content'], str):
                    data = json.loads(r['content'])
                else:
                    data = r['content']
                    
                # [Holiday Skip]
                if data.get("is_trading_day") is False:
                    continue
                    
                daily_jsons.append(data)
            except:
                continue
                
        if not daily_jsons:
            print("   ⚠️ No valid daily JSONs extracted.")
            return None
            
        daily_reports_json_str = json.dumps(daily_jsons, indent=2)
        
        # 3. Construct Prompt
        # Note: We are feeding Daily Reports into Monthly Prompt. 
        # We need to ensure the prompt handles this. 
        # I will dynamically adjust the prompt text here if needed, or update prompts.py.
        # Let's assume prompts.py will be updated to say "Daily Reports" or we just replace the placeholder.
        
        month_str = start_date[:7] # YYYY-MM
        
        prompt = MONTHLY_REPORT_PROMPT.replace("{month}", month_str)\
            .replace("{weekly_reports_json}", daily_reports_json_str) # Re-using the placeholder name but passing daily data
            
        # 4. Call LLM
        try:
            response_json_str = ask_llm(prompt, model=self.model, system_prompt=DEEPSEEK_SYSTEM_PROMPT)
            
            if "```json" in response_json_str:
                response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_json_str:
                response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
                
            report_data = json.loads(response_json_str)
            
            # 5. Save to DB
            self._save_report(month_str, country, report_data)
            return report_data
            
        except Exception as e:
            print(f"   ❌ Monthly Generation Failed: {e}")
            return None

    def _fetch_daily_reports(self, start_date: str, end_date: str, country: str) -> List[Dict]:
        try:
            # daily_reports -> reports_daily
            res = self.supabase.table("reports_daily")\
                .select("date, report_json")\
                .eq("country", country)\
                .gte("date", start_date)\
                .lte("date", end_date)\
                .order("date")\
                .execute()
            return res.data or []
        except Exception as e:
            print(f"   ⚠️ Failed to fetch daily reports: {e}")
            return []

    def _save_report(self, month: str, country: str, data: Dict):
        try:
            summary_lines = data.get("executive_summary", [])
            summary_text = "\n".join(summary_lines) if isinstance(summary_lines, list) else str(summary_lines)
            
            payload = {
                "month": month,
                "country": country,
                "report_json": json.dumps(data),
                "summary": summary_text,
                "created_at": "now()"
            }
            # monthly_summaries -> reports_monthly
            self.supabase.table("reports_monthly").insert(payload).execute()
        except Exception as e:
            if "duplicate key" in str(e) or "23505" in str(e):
                print(f"   ⏭️ Monthly Report for {month} already exists.")
            else:
                print(f"   ⚠️ Failed to save monthly report: {e}")

if __name__ == "__main__":
    gen = MonthlyReportGenerator()
    gen.generate("2023-01-01", "2023-01-31", "US")
