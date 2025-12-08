import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
import argparse

# Configuration
MAX_WORKERS = 8  # Safe limit for MacBook Air & API Rate Limits

def run_year(year):
    """
    Runs batch_generate_reports.py for a specific year.
    """
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    print(f"🚀 [Launcher] Starting Worker for Year {year}...")
    
    cmd = [
        "python3", "batch_generate_reports.py",
        "--start", start_date,
        "--end", end_date,
        "--countries", "GLOBAL"
    ]
    
    try:
        # Run command and wait for it to complete
        # We capture output to avoid terminal clutter, or let it stream?
        # Let's let it stream but prefix it? Hard to prefix in subprocess easily without piping.
        # For simplicity, let's just run it. The logs might interleave, but that's okay for now.
        subprocess.run(cmd, check=True)
        print(f"✅ [Launcher] Finished Year {year}")
    except subprocess.CalledProcessError as e:
        print(f"❌ [Launcher] Failed Year {year}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Parallel Batch Launcher")
    parser.add_argument("--start_year", type=int, default=2000, help="Start Year")
    parser.add_argument("--end_year", type=int, default=2025, help="End Year")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of concurrent workers")
    
    args = parser.parse_args()
    
    years = list(range(args.start_year, args.end_year + 1))
    print(f"🏎️  Starting Parallel Generation for {len(years)} years ({args.start_year}-{args.end_year})")
    print(f"🔥 Concurrency: {args.workers} workers")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        executor.map(run_year, years)
        
    print("🎉 All years completed!")

if __name__ == "__main__":
    main()
