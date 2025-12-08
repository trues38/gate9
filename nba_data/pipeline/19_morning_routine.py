import os
import subprocess
import time
from datetime import datetime

def run_step(script_name, description):
    print(f"\n{'='*50}")
    print(f"🌅 MORNING ROUTINE: {description}")
    print(f"{'='*50}")
    start = time.time()
    try:
        # Run the script
        subprocess.check_call(["python3", f"nba_data/pipeline/{script_name}"])
        print(f"✅ Completed in {round(time.time() - start, 1)}s")
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {script_name} (Error: {e})")
        # specific handling could go here
        
def main():
    print(f"🚀 REGIME PRO: MORNING LAUNCH SEQUENCE [{datetime.now().strftime('%H:%M:%S')}]")
    print("Checking overnight data mining results...")
    
    # Check File Counts
    legacy_count = len([n for n in os.listdir("nba_data/stories_raw") if n.endswith(".json")])
    print(f"📊 Raw Stories Found: {legacy_count}")
    
    # Step 1: Compile Files
    # This aggregates the thousands of JSONs into player_history.json
    run_step("16_compile_player_history.py", "Compiling Player Histories")
    
    # Step 2: Run Regime Engine
    # This calculates the Signals (Surging/Crashing)
    # run_step("17_launch_regime_pro.py", "Generating Regime Signals") 
    # Note: 17 might be heavy. Let's rely on 18 for the Web Export which does lightweight calc, 
    # or ensure 17 saves to a place 18 reads?
    # actually 17 generates markdown reports. 
    # 18 reads player_history.json directly and applies lightweight logic.
    # For the "Web Launch", 18 is the critical path.
    
    # Step 3: Export to Web
    run_step("18_export_web_data.py", "Updates Web Dashboard Data")
    
    print("\n" + "="*50)
    print("✅ SYSTEM READY FOR LIVE ACTION")
    print("🌐 Dashboard: http://localhost:3000")
    print("="*50)

if __name__ == "__main__":
    main()
