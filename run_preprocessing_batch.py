import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from g9_macro_factory.engine.daily_preprocessor import DailyPreprocessor

def process_date(args):
    date_str, country = args
    processor = DailyPreprocessor()
    success = processor.process(date_str, country)
    if success:
        # print(f"✅ {date_str}")
        pass
    else:
        print(f"❌ {date_str}")

def run_batch_preprocessing(start_date_str, end_date_str, country="GLOBAL", workers=10):
    print(f"🚀 Starting Batch Preprocessing ({start_date_str} ~ {end_date_str})...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append((current_date.strftime("%Y-%m-%d"), country))
        current_date += timedelta(days=1)
        
    print(f"🔥 Processing {len(dates)} days with {workers} threads...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        executor.map(process_date, dates)
        
    print("✅ Batch Preprocessing Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Preprocessing")
    parser.add_argument("--start", type=str, required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--country", type=str, default="GLOBAL", help="Country Code")
    parser.add_argument("--workers", type=int, default=10, help="Concurrency")
    
    args = parser.parse_args()
    
    run_batch_preprocessing(args.start, args.end, args.country, args.workers)
