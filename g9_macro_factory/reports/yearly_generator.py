import os
import sys
import json
from typing import Dict, List

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client
from utils.openrouter_client import ask_llm
from g9_macro_factory.prompts import DEEPSEEK_SYSTEM_PROMPT, YEARLY_REPORT_PROMPT

class YearlyReportGenerator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.model = "x-ai/grok-4.1-fast:free"

    def generate(self, start_date: str, end_date: str, country: str = "US"):
        year = start_date[:4]
        print(f"   📅 Generating Yearly Report for {year} ({country})...")
        
        # 1. Fetch Monthly Reports (Recursive)
        monthly_reports = self._fetch_monthly_reports(year, country)
        if not monthly_reports:
            print(f"   ⚠️ No monthly reports found for {year}. Skipping.")
            return None
            
        # 2. Prepare JSONs
        monthly_jsons = []
        for r in monthly_reports:
            try:
                if isinstance(r['content'], str):
                    monthly_jsons.append(json.loads(r['content']))
                else:
                    monthly_jsons.append(r['content'])
            except:
                continue
                
        if not monthly_jsons:
            print("   ⚠️ No valid monthly JSONs extracted.")
            return None
            
        monthly_reports_json_str = json.dumps(monthly_jsons, indent=2)
        
        # 3. Construct Prompt
        prompt = YEARLY_REPORT_PROMPT.replace("{year}", year)\
            .replace("{monthly_reports_json}", monthly_reports_json_str)
            
        # 4. Call LLM
        try:
            response_json_str = ask_llm(prompt, model=self.model, system_prompt=DEEPSEEK_SYSTEM_PROMPT)
            
            if "```json" in response_json_str:
                response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_json_str:
                response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
                
            report_data = json.loads(response_json_str)
            
            # 5. Save to DB
            self._save_report(year, country, report_data)
            return report_data
            
        except Exception as e:
            print(f"   ❌ Yearly Generation Failed: {e}")
            return None

    def _fetch_monthly_reports(self, year: str, country: str) -> List[Dict]:
        try:
            # Fetch all months for the year
            # monthly_summaries -> reports_monthly
            start_month = f"{year}-01"
            end_month = f"{year}-12"
            
            res = self.supabase.table("reports_monthly")\
                .select("month, report_json")\
                .eq("country", country)\
                .gte("month", start_month)\
                .lte("month", end_month)\
                .order("month")\
                .execute()
            return res.data or []
        except Exception as e:
            print(f"   ⚠️ Failed to fetch monthly reports: {e}")
            return []

    def _save_report(self, year: str, country: str, data: Dict):
        try:
            summary_lines = data.get("executive_summary", [])
            summary_text = "\n".join(summary_lines) if isinstance(summary_lines, list) else str(summary_lines)
            
            payload = {
                "year": int(year),
                "country": country,
                "report_json": json.dumps(data),
                "summary": summary_text,
                "created_at": "now()"
            }
            # yearly_summaries -> reports_annual
            self.supabase.table("reports_annual").insert(payload).execute()
        except Exception as e:
            if "duplicate key" in str(e) or "23505" in str(e):
                print(f"   ⏭️ Yearly Report for {year} already exists.")
            else:
                print(f"   ⚠️ Failed to save yearly report: {e}")

if __name__ == "__main__":
    gen = YearlyReportGenerator()
    gen.generate("2023-01-01", "2023-12-31", "US")
