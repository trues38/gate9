import os
import sys
import argparse
from datetime import datetime, timedelta
import calendar

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g9_macro_factory.config import get_supabase_client
from g9_macro_factory.reports.daily_generator import DailyReportGenerator
from g9_macro_factory.reports.weekly_generator import WeeklyReportGenerator
from g9_macro_factory.reports.monthly_generator import MonthlyReportGenerator
from g9_macro_factory.reports.yearly_generator import YearlyReportGenerator
from utils.openrouter_client import ask_llm

class Orchestrator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.daily_gen = DailyReportGenerator()
        self.weekly_gen = WeeklyReportGenerator()
        self.monthly_gen = MonthlyReportGenerator()
        self.yearly_gen = YearlyReportGenerator()

    def run_preflight_checks(self):
        print("🔍 Running Pre-flight Checks...", flush=True)
        
        # 1. DB Check
        try:
            self.supabase.table("global_news_all").select("id").limit(1).execute()
            print("   ✅ DB Connection (global_news_all): PASS", flush=True)
        except Exception as e:
            print(f"   ❌ DB Connection Failed: {e}", flush=True)
            return False
            
        # 2. LLM Check
        try:
            ask_llm("ping", model="deepseek/deepseek-chat")
            print("   ✅ LLM Connection (DeepSeek V3): PASS", flush=True)
        except Exception as e:
            print(f"   ❌ LLM Connection Failed: {e}", flush=True)
            return False
            
        return True

    def check_data_availability(self, start_year: int, end_year: int):
        print(f"🔍 Checking Data Availability ({start_year}-{end_year})...", flush=True)
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        
        # 1. News Check
        try:
            res = self.supabase.table('global_news_all').select('count', count='exact').gte('published_at', start_date).lte('published_at', end_date).execute()
            count = res.count
            if count == 0:
                print(f"   ❌ No News found for {start_year}-{end_year}!", flush=True)
                return False
            print(f"   ✅ News Data: {count} records found.", flush=True)
        except Exception as e:
            print(f"   ⚠️ News Check Failed (likely timeout): {e}. Proceeding anyway...", flush=True)
            # return True # Allow proceed
            
        # 2. Z-Score Check
        try:
            res = self.supabase.table('zscore_daily').select('count', count='exact').gte('date', start_date).lte('date', end_date).execute()
            count = res.count
            if count == 0:
                print(f"   ⚠️ No Z-Score data found for {start_year}-{end_year}! Proceeding anyway...", flush=True)
            else:
                print(f"   ✅ Z-Score Data: {count} records found.", flush=True)
        except Exception as e:
            print(f"   ⚠️ Z-Score Check Failed: {e}. Proceeding anyway...", flush=True)
            
        return True

    def run_pipeline(self, start_year: int, end_year: int, country: str = "US"):
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        self.run_pipeline_custom(start_date, end_date, country)

    def run_pipeline_custom(self, start_date_str: str, end_date_str: str, country: str = "US"):
        if not self.run_preflight_checks():
            return
            
        # Extract years for data check
        start_year = int(start_date_str.split("-")[0])
        end_year = int(end_date_str.split("-")[0])
        
        if not self.check_data_availability(start_year, end_year):
            print("🛑 Pre-flight Data Check Failed. Aborting.")
            return

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        current_date = start_date

        print(f"🏭 Starting Orchestration Pipeline ({start_date_str} to {end_date_str})...", flush=True)

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            print(f"   ➡️ Processing Date: {date_str}", flush=True)
            
            # 1. Daily Report
            # Check if exists first (Cost Saving)
            if self._report_exists("daily_reports", date_str, country):
                print(f"   ⏭️ Daily Report for {date_str} exists. Skipping.", flush=True)
            else:
                print(f"   ⚡ Generating Daily Report for {date_str}...", flush=True)
                self.daily_gen.generate(date_str, country)


            
            # 2. Weekly Report (Run on Sundays)
            if current_date.weekday() == 6: # Sunday
                monday = current_date - timedelta(days=6)
                monday_str = monday.strftime("%Y-%m-%d")
                sunday_str = current_date.strftime("%Y-%m-%d")
                
                # Check if exists
                if self._report_exists("weekly_summaries", monday_str, country, date_col="start_date"):
                     print(f"   ⏭️ Weekly Report for {monday_str} exists. Skipping.", flush=True)
                else:
                    # [Certification Point 1] Date-Based Aggregation
                    self.weekly_gen.generate(monday_str, sunday_str, country)
                
            # 3. Monthly Report (Run on Last Day of Month)
            last_day_of_month = calendar.monthrange(current_date.year, current_date.month)[1]
            if current_date.day == last_day_of_month:
                month_start = current_date.replace(day=1)
                month_start_str = month_start.strftime("%Y-%m-%d")
                month_end_str = current_date.strftime("%Y-%m-%d")
                month_key = current_date.strftime("%Y-%m") # For DB check
                
                if self._report_exists("monthly_summaries", month_key, country, date_col="month"):
                    print(f"   ⏭️ Monthly Report for {month_key} exists. Skipping.", flush=True)
                else:
                    self.monthly_gen.generate(month_start_str, month_end_str, country)
                
            # 4. Yearly Report (Run on Last Day of Year)
            if current_date.month == 12 and current_date.day == 31:
                year_start_str = f"{current_date.year}-01-01"
                year_end_str = f"{current_date.year}-12-31"
                
                if self._report_exists("yearly_summaries", current_date.year, country, date_col="year"):
                     print(f"   ⏭️ Yearly Report for {current_date.year} exists. Skipping.", flush=True)
                else:
                    self.yearly_gen.generate(year_start_str, year_end_str, country)
                
                self.trigger_backtest(current_date.year)
            
            current_date += timedelta(days=1)

    def _report_exists(self, table: str, date_val, country: str, date_col: str = "date") -> bool:
        try:
            res = self.supabase.table(table)\
                .select("id")\
                .eq(date_col, date_val)\
                .eq("country", country)\
                .limit(1)\
                .execute()
            return len(res.data) > 0
        except:
            return False

    def trigger_backtest(self, year: int):
        print(f"   ⚔️ Triggering Backtest for {year}...")
        # We call the run_full_history.py script as a subprocess or import it.
        # Subprocess is safer to avoid memory leaks over long runs.
        import subprocess
        try:
            cmd = [
                "python3", 
                "g9_macro_factory/backtest/run_full_history.py",
                "--start_year", str(year),
                "--end_year", str(year),
                "--loops", "1" # Single pass for verification
            ]
            subprocess.run(cmd, check=True)
            print(f"   ✅ Backtest for {year} Completed.")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Backtest for {year} Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_year', type=int, default=2023)
    parser.add_argument('--end_year', type=int, default=2023)
    parser.add_argument('--country', type=str, default="US")
    parser.add_argument("--start_date", type=str, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, help="End Date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator()
    
    if args.start_date and args.end_date:
        # Custom Date Range Mode
        start_year = int(args.start_date.split("-")[0])
        end_year = int(args.end_date.split("-")[0])
        orchestrator.run_pipeline_custom(args.start_date, args.end_date, args.country)
    else:
        orchestrator.run_pipeline(args.start_year, args.end_year, args.country)
