import math

def generate_commands():
    start_year = 2000
    end_year = 2025
    total_years = end_year - start_year + 1
    num_workers = 8
    
    # Calculate years per worker
    years_per_worker = math.ceil(total_years / num_workers)
    
    print(f"🚀 Generating 8-Way Parallel Commands for {total_years} Years ({start_year}-{end_year})")
    print(f"ℹ️  Configuration: 4 Computers x 2 Terminals = 8 Workers")
    print(f"ℹ️  Workload: ~{years_per_worker} years per worker\n")
    
    worker_id = 1
    current_year = start_year
    
    while current_year <= end_year:
        chunk_end_year = min(current_year + years_per_worker - 1, end_year)
        
        # Format dates
        start_date = f"{current_year}-01-01"
        end_date = f"{chunk_end_year}-12-31"
        
        # Determine Computer and Terminal ID
        computer_id = math.ceil(worker_id / 2)
        terminal_id = 1 if worker_id % 2 != 0 else 2
        
        print(f"💻 [Computer {computer_id} / Terminal {terminal_id}] (Worker {worker_id})")
        print(f"   Range: {start_date} ~ {end_date}")
        print(f"   Command: python3 ticker_global/news_summary_pipeline.py --start_date {start_date} --end_date {end_date}")
        print("-" * 60)
        
        current_year = chunk_end_year + 1
        worker_id += 1

if __name__ == "__main__":
    generate_commands()
