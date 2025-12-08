import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.backtest_engine.backtest_runner import run_backtest_for_date
from g9_macro_factory.memory_core.summary_report import print_summary

def get_zscore_dates(limit=10, csv_path="zscore_daily.csv"):
    """Fetches top Z-Score dates from CSV or DB."""
    # Priority 1: Local CSV
    if os.path.exists(csv_path):
        print(f"   📂 Loading dates from {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
            # Sort by z_year (absolute magnitude? or just high?)
            # User said "2.0 이상 튀어오른". Usually positive.
            # Let's sort by z_year descending.
            # Sort by impact_score if available (Hybrid Score)
            if 'impact_score' in df.columns:
                print("   🔥 Sorting by Hybrid Impact Score (Z-Score * ln(Volume))...")
                df = df.sort_values('impact_score', ascending=False)
            elif 'z_year' in df.columns:
                df = df.sort_values('z_year', ascending=False)
            elif 'z_score' in df.columns:
                df = df.sort_values('z_score', ascending=False)
            
            dates = df['date'].head(limit).tolist()
            print(f"   🎯 Selected Top {len(dates)} dates based on Z-Score.")
            return dates
        except Exception as e:
            print(f"   ⚠️ Failed to load CSV: {e}")
            
    # Priority 2: DB (Not implemented here to avoid complexity, assume CSV is generated)
    # If DB needed, we would use supabase client.
    
    return []

def main():
    parser = argparse.ArgumentParser(description="Run G9 Macro-Factory Backtest")
    parser.add_argument("--days", type=int, default=5, help="Number of days to backtest (or Limit for Z-Score mode)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD). Default: 60 days ago")
    parser.add_argument("--step", type=int, default=3, help="Step size in days between tests")
    parser.add_argument("--threads", type=int, default=5, help="Number of parallel threads (Default: 5)")
    parser.add_argument("--mode", type=str, default="sequential", choices=["sequential", "zscore", "hybrid"], help="Execution mode")
    parser.add_argument("--zscore-file", type=str, default="zscore_daily.csv", help="Path to Z-Score CSV")
    
    args = parser.parse_args()
    
    print(f"🏁 Starting G9 Macro-Factory Backtest (Mode: {args.mode}, Limit: {args.days}, Threads: {args.threads})")
    
    dates = []
    
    if args.mode == "zscore":
        dates = get_zscore_dates(limit=args.days, csv_path=args.zscore_file)
        if not dates:
            print("   ❌ No dates found from Z-Score. Falling back to sequential.")
            args.mode = "sequential"
            
    if args.mode == "hybrid":
        # 1. Get Z-Score Dates
        z_dates = get_zscore_dates(limit=args.days * 2, csv_path=args.zscore_file) # Get more to find overlap
        
        # 2. Get History Dates
        h_dates = []
        history_path = os.path.join(os.path.dirname(__file__), "g9_macro_factory/data/history_events.csv")
        if os.path.exists(history_path):
            print(f"   📜 Loading History Events from {history_path}...")
            df_hist = pd.read_csv(history_path)
            h_dates = df_hist['date'].tolist()
            print(f"   🏛️ Found {len(h_dates)} Historical Events.")
        else:
            print(f"   ⚠️ History file not found at {history_path}")
            
        # 3. Merge & Prioritize
        # Convert to sets for easy operation
        z_set = set(z_dates)
        h_set = set(h_dates)
        
        # Overlap (Double Weight)
        overlap = z_set.intersection(h_set)
        print(f"   ⚔️ Hybrid Synergy: {len(overlap)} events found in BOTH lists! (Double Weight)")
        
        # Union
        combined = list(z_set.union(h_set))
        combined.sort()
        
        # Filter out pre-2000 dates (No Macro Data)
        original_count = len(combined)
        combined = [d for d in combined if d >= "2000-01-01"]
        filtered_count = original_count - len(combined)
        if filtered_count > 0:
            print(f"   🧹 Filtered out {filtered_count} pre-2000 dates (No Data).")
        
        # If limit is set, how do we choose?
        # Priority: Overlap > History > High Z-Score
        # For now, let's just take all combined, or limit if too many?
        # User said "Merge". Let's use all of them but maybe limit total count if needed.
        # But args.days is usually small (5).
        # Let's respect args.days as a "minimum" or just run all?
        # "Limit for Z-Score mode" implies we limit Z-Score.
        # Let's return ALL combined dates for now, as History is curated.
        dates = combined
        print(f"   🚀 Hybrid Target List: {len(dates)} dates ready for backtest.")
            
            
    if args.mode == "sequential":
        if args.start:
            base_date = datetime.fromisoformat(args.start).date()
        else:
            base_date = datetime.now().date() - timedelta(days=60)
            
        dates = [(base_date + timedelta(days=i*args.step)).isoformat() for i in range(args.days)]
    
    results = []
    
    # Load Score Map (Date -> {z_score, impact_score})
    score_map = {}
    if os.path.exists(args.zscore_file):
        try:
            df = pd.read_csv(args.zscore_file)
            for _, row in df.iterrows():
                d_str = row['date']
                # Map CSV columns to expected keys
                # CSV might have 'z_day_local' instead of 'z_score'
                z_val = row.get('z_score')
                if pd.isna(z_val):
                    z_val = row.get('z_day_local', 0.0)
                    
                score_map[d_str] = {
                    "z_score": float(z_val),
                    "impact_score": float(row.get('impact_score', 0.0))
                }
            print(f"✅ Loaded Z-Score Data ({len(score_map)} days)")
        except Exception as e:
            print(f"❌ Error loading Z-Score file: {e}")
    else:
        print(f"⚠️ Z-Score file not found: {args.zscore_file}")

    # Parallel Execution
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # Pass score data if available
        future_to_date = {}
        for d in dates:
            scores = score_map.get(d, {"z_score": 0.0, "impact_score": 0.0})
            future_to_date[executor.submit(run_backtest_for_date, d, scores)] = d
        
        for future in as_completed(future_to_date):
            d = future_to_date[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as e:
                print(f"   ❌ Error processing {d}: {e}")
            
    print_summary(results)
    
    print(f"\nREADY FOR {len(dates)} RUN")

if __name__ == "__main__":
    main()
