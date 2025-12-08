import argparse
from datetime import datetime, timedelta
from no_session_injector import inject_no_session

def run_holiday_cleaner(start_date_str, end_date_str, countries=["GLOBAL"]):
    print(f"🧹 Starting Holiday Cleaner ({start_date_str} ~ {end_date_str})...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    current_date = start_date
    count = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        for country in countries:
            # inject_no_session checks if it IS a holiday/weekend internally
            # and only injects if true.
            injected = inject_no_session(date_str, country)
            if injected:
                count += 1
                
        current_date += timedelta(days=1)
        
    print(f"✅ Holiday Cleaner Complete. Injected {count} No-Session records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Holiday Cleaner (Batch Tagging)")
    parser.add_argument("--start", type=str, required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--countries", type=str, default="GLOBAL", help="Comma-separated Country Codes")
    
    args = parser.parse_args()
    country_list = [c.strip() for c in args.countries.split(",")]
    
    run_holiday_cleaner(args.start, args.end, country_list)
