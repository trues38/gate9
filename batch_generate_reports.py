import os
import sys
import argparse
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.reports.daily_generator import DailyReportGenerator
from g9_macro_factory.reports.weekly_generator import WeeklyReportGenerator
from g9_macro_factory.reports.monthly_generator import MonthlyReportGenerator
from g9_macro_factory.reports.yearly_generator import YearlyReportGenerator

def run_batch_generation(start_date_str, end_date_str, countries=["GLOBAL"]):
    print(f"🚀 Starting Batch Report Generation ({start_date_str} ~ {end_date_str}) for {countries}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    daily_gen = DailyReportGenerator()
    weekly_gen = WeeklyReportGenerator()
    monthly_gen = MonthlyReportGenerator()
    yearly_gen = YearlyReportGenerator()
    
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n📅 Processing Date: {date_str}")
        
        for country in countries:
            # 1. Generate Daily Report
            try:
                daily_gen.generate(date_str, country)
            except Exception as e:
                print(f"   ❌ Daily Gen Error ({date_str}, {country}): {e}")
                
            # 2. Check for Weekly Report (Sunday)
            if current_date.weekday() == 6: # Sunday
                week_start = (current_date - timedelta(days=6)).strftime("%Y-%m-%d")
                week_end = date_str
                try:
                    weekly_gen.generate(week_start, week_end, country)
                except Exception as e:
                    print(f"   ❌ Weekly Gen Error ({week_start}~{week_end}, {country}): {e}")
                    
            # 3. Check for Monthly Report (Last Day of Month)
            tomorrow = current_date + timedelta(days=1)
            if tomorrow.day == 1:
                month_start = current_date.replace(day=1).strftime("%Y-%m-%d")
                month_end = date_str
                try:
                    monthly_gen.generate(month_start, month_end, country)
                except Exception as e:
                    print(f"   ❌ Monthly Gen Error ({month_start}~{month_end}, {country}): {e}")
                    
            # 4. Check for Yearly Report (Dec 31)
            if current_date.month == 12 and current_date.day == 31:
                year_str = str(current_date.year)
                try:
                    yearly_gen.generate(year_str, country)
                except Exception as e:
                    print(f"   ❌ Yearly Gen Error ({year_str}, {country}): {e}")
        
        current_date += timedelta(days=1)
        
    print("✅ Batch Generation Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Generate Reports")
    parser.add_argument("--start", type=str, required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--countries", type=str, default="GLOBAL", help="Comma-separated Country Codes (default: GLOBAL)")
    
    args = parser.parse_args()
    country_list = [c.strip() for c in args.countries.split(",")]
    
    run_batch_generation(args.start, args.end, country_list)
