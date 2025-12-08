import time
import subprocess
import datetime
import sys

def run_script(script_name):
    print(f"\n🔄 [{datetime.datetime.now().strftime('%H:%M:%S')}] Running {script_name}...")
    try:
        subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {script_name} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed with error: {e}")
    except Exception as e:
        print(f"❌ An error occurred while running {script_name}: {e}")

def main():
    print("🚀 Starting Regime Zero Local Automation Loop")
    print("   - Ingestion: Every 30 minutes")
    print("   - Refinement: Every 5 minutes")
    
    last_ingest = 0
    ingest_interval = 10 * 60  # 10 minutes
    
    last_refine = 0
    refine_interval = 5 * 60   # 5 minutes

    while True:
        current_time = time.time()

        # Run Ingestion
        if current_time - last_ingest > ingest_interval:
            run_script("engine/run_daily_ingest.py")
            last_ingest = time.time()

        # Run Refinement
        if current_time - last_refine > refine_interval:
            run_script("engine/refine_news.py")
            last_refine = time.time()

        # Sleep to prevent CPU spinning
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Loop stopped by user.")
