import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
import argparse

# Configuration
MAX_WORKERS = 10  # High concurrency for Preprocessing (No LLM, just DB I/O)

def run_year_preprocessing(year):
    """
    Runs run_preprocessing_batch.py for a specific year.
    """
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    print(f"🚀 [Launcher] Starting Preprocessing for Year {year}...")
    
    countries = ["US", "KR", "JP", "CN"]
    
    for country in countries:
        # We can run countries in parallel or sequence per year.
        # To avoid exploding threads (10 years * 4 countries = 40 threads), 
        # let's run countries sequentially within each year-worker, 
        # OR just pass the list to run_preprocessing_batch if it supports it.
        # run_preprocessing_batch currently takes single country.
        # Let's update run_preprocessing_batch to take a list or loop here.
        
        # Actually, let's update run_preprocessing_batch.py to handle multiple countries.
        # But for now, let's just loop here in the command.
        cmd = [
            "python3", "run_preprocessing_batch.py",
            "--start", start_date,
            "--end", end_date,
            "--country", country,
            "--workers", "5"
        ]
        try:
            subprocess.run(cmd, check=True)
        except:
            print(f"❌ Failed {country} for {year}")
            
    print(f"✅ [Launcher] Finished Year {year} (All Countries)")

def main():
    parser = argparse.ArgumentParser(description="Parallel Preprocessor Launcher (Distributed)")
    parser.add_argument("--start_year", type=int, default=2000, help="Start Year")
    parser.add_argument("--end_year", type=int, default=2025, help="End Year")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of concurrent year-workers per node")
    parser.add_argument("--node_id", type=int, default=0, help="Node ID (0-indexed) for distributed processing")
    parser.add_argument("--total_nodes", type=int, default=1, help="Total number of nodes/computers")
    
    args = parser.parse_args()
    
    # 1. Generate all target years
    all_years = list(range(args.start_year, args.end_year + 1))
    
    # 2. Assign years to this node (Modulo Sharding)
    my_years = [y for y in all_years if y % args.total_nodes == args.node_id]
    
    print(f"🏎️  Starting Distributed Preprocessing (Node {args.node_id}/{args.total_nodes})")
    print(f"📅 Assigned Years: {my_years}")
    print(f"🔥 Local Concurrency: {args.workers} threads")
    
    if not my_years:
        print("   ⚠️ No years assigned to this node. Exiting.")
        return

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        executor.map(run_year_preprocessing, my_years)
        
    print(f"🎉 Node {args.node_id} Finished!")

if __name__ == "__main__":
    main()
