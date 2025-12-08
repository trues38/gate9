import os
import sys
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.summarizer.weekly_builder import WeeklyBuilder
from g9_macro_factory.summarizer.monthly_builder import MonthlyBuilder

def run_build_summaries(start_year, end_year, country="US"):
    print(f"🚀 Starting Summary Build for {country} ({start_year}-{end_year})...")
    
    weekly_builder = WeeklyBuilder()
    monthly_builder = MonthlyBuilder()
    
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    current = start_date
    
    # Iterate by week
    # Find first Monday
    while current.weekday() != 0:
        current += timedelta(days=1)
        
    while current <= end_date:
        # Build Weekly
        week_start_str = current.strftime("%Y-%m-%d")
        print(f"Processing Week: {week_start_str}...", end="\r")
        weekly_builder.build_weekly_summary(week_start_str, country)
        
        # Check if month changed, if so, build previous month
        # Simple logic: just build monthly for every month in range
        # Optimized: Build monthly at end of month loop?
        # Let's just iterate months separately to be safe.
        
        current += timedelta(days=7)
        
    print("\n✅ Weekly Summaries Complete.")
    
    # Iterate by Month
    current_m = datetime(start_year, 1, 1)
    while current_m <= end_date:
        month_str = current_m.strftime("%Y-%m-%d")
        print(f"Processing Month: {month_str}...", end="\r")
        monthly_builder.build_monthly_summary(month_str, country)
        current_m += relativedelta(months=1)
        
    print("\n✅ Monthly Summaries Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_year', type=int, default=2023)
    parser.add_argument('--end_year', type=int, default=2023)
    parser.add_argument('--country', type=str, default="US", help="Country code (US, KR, CN, JP) or 'ALL'")
    args = parser.parse_args()
    
    if args.country.upper() == "ALL":
        countries = ["US", "KR", "CN", "JP"]
    else:
        countries = [args.country]
        
    for c in countries:
        run_build_summaries(args.start_year, args.end_year, c)
