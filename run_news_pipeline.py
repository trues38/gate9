import time
import subprocess
import threading
from datetime import datetime

# Configuration
FETCH_LIVE_INTERVAL_SECONDS = 600 # 10 Minutes
FETCH_MACRO_INTERVAL_SECONDS = 1800 # 30 Minutes
PROCESS_INTERVAL_SECONDS = 10

def run_script(script_path):
    """Runs a python script and logs output."""
    print(f"[{datetime.now()}] 🚀 Running {script_path}...")
    try:
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            # Print only first 2 lines of output to keep log clean
            output_lines = result.stdout.strip().split('\n')
            summary = '\n'.join(output_lines[:2]) + ("..." if len(output_lines) > 2 else "")
            print(f"[{datetime.now()}] ✅ {script_path} Finished. {summary}")
        else:
            print(f"[{datetime.now()}] ❌ {script_path} Failed.\n{result.stderr}")
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ Error running {script_path}: {e}")

def loop_fetch_live():
    while True:
        run_script("deploy_g9/fetch_live_news.py")
        time.sleep(FETCH_LIVE_INTERVAL_SECONDS)

def loop_fetch_macro():
    while True:
        run_script("regime_zero/ingest/fetch_macro_news.py")
        time.sleep(FETCH_MACRO_INTERVAL_SECONDS)

def loop_process_raw():
    while True:
        run_script("regime_zero/engine/process_raw_news.py")
        time.sleep(PROCESS_INTERVAL_SECONDS)

if __name__ == "__main__":
    print("🔄 Starting News Pipeline Manager...")
    print(f"   - Live News: Every {FETCH_LIVE_INTERVAL_SECONDS}s")
    print(f"   - Macro News: Every {FETCH_MACRO_INTERVAL_SECONDS}s")
    print(f"   - Processor: Every {PROCESS_INTERVAL_SECONDS}s")
    
    # Create threads
    t1 = threading.Thread(target=loop_fetch_live, daemon=True)
    t2 = threading.Thread(target=loop_fetch_macro, daemon=True)
    t3 = threading.Thread(target=loop_process_raw, daemon=True)
    
    # Start threads
    t1.start()
    t2.start()
    t3.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Pipeline Stopped.")
