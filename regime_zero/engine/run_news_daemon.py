import time
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.engine.process_raw_news import run_processing
from regime_zero.engine.run_daily_ingest import fetch_news

def news_daemon():
    print(f"🚀 G9 NEWS DAEMON STARTED [{datetime.now()}]")
    print("   Cycle: Fetch -> Process (Stage 1 Fast -> Stage 2 Deep) -> Sleep")
    
    while True:
        try:
            print(f"\n⏰ Tick: {datetime.now().strftime('%H:%M:%S')}")
            
            # 1. Ingest (Fetch new RSS items)
            # We run this less frequently, maybe every 10 mins? 
            # For now, let's run it every loop but fetch_news handles dedup via DB constraints.
            print("   📡 Checking for new headlines...")
            fetch_news()
            
            # 2. Process (Refine & Score)
            # We loop this until queue is empty to clear backlog
            print("   ⚙️  Processing queue...")
            while True:
                # run_processing processes a batch of 20. 
                # We can modify run_processing to return count, or just run it blindly.
                # Since run_processing prints output, we'll just call it.
                # To know if we should stop, we'd need run_processing to return "processed_count".
                # For now, let's run it 5 times max per tick to avoid hogging if huge backlog.
                for _ in range(5):
                    run_processing()
                    time.sleep(1) # Breath
                break
                
            print("   💤 Sleeping for 5 minutes...")
            time.sleep(300) # 5 minutes
            
        except KeyboardInterrupt:
            print("\n🛑 Daemon stopped by user.")
            break
        except Exception as e:
            print(f"   ❌ Daemon Error: {e}")
            time.sleep(60) # Sleep on error

if __name__ == "__main__":
    news_daemon()
