import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
START_YEAR = 2015
END_YEAR = 2024
MAX_WORKERS = 4 # Safe limit to avoid rate limits

def run_crawl(year):
    output_file = f"btc_news_{year}.csv"
    cmd = [
        "python3", "regime_zero/ingest/fetch_btc_news.py",
        "--start", str(year),
        "--end", str(year),
        "--output", output_file
    ]
    print(f"🚀 Starting Crawl for {year} -> {output_file}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Completed {year}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed {year}: {e}")

def main():
    years = list(range(START_YEAR, END_YEAR + 1))
    
    print(f"🔥 Launching Parallel Crawl for {len(years)} years with {MAX_WORKERS} workers...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(run_crawl, years)
        
    print("🎉 All crawls completed.")
    
    # Merge Step (Optional, or user can do it later)
    # For now, let's just notify completion.

if __name__ == "__main__":
    main()
