import os
import subprocess
import time

def run_step(description, command):
    print(f"\n🚀 Starting: {description}...")
    start_time = time.time()
    try:
        subprocess.run(command, check=True, shell=True)
        elapsed = time.time() - start_time
        print(f"✅ Completed: {description} in {elapsed:.2f}s")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}")
        print(f"Error: {e}")
        exit(1)

def main():
    print("🔥 Regime Zero: Full Pipeline (Aggregation -> Indexing)")
    
    # 1. Aggregate Regimes (Hybrid: News + Price Fallback)
    run_step("Regime Aggregation", "PYTHONPATH=. python3 regime_zero/engine/regime_aggregator.py")
    
    # 2. Build Vector Index (TF-IDF)
    run_step("Vector Indexing", "PYTHONPATH=. python3 regime_zero/engine/vector_indexer.py")
    
    print("\n✨ Pipeline Complete! The Regime Matcher is now ready with the latest data.")

if __name__ == "__main__":
    main()
