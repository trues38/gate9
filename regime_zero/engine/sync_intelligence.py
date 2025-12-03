import os
import sys
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

REGIME_FILE = "regime_zero/data/regime_objects.jsonl"
REPORTS_DIR = "regime_zero/reports/consensus"

def create_tables_if_not_exist():
    """
    Attempts to create tables via SQL RPC or just assumes they exist.
    Since we can't easily run DDL via REST without a specific RPC,
    we will try to assume they exist. If not, we print a warning.
    
    Ideally, the user should run the SQL manually or we use a privileged RPC.
    But for now, let's try to proceed.
    """
    print("ℹ️  Ensuring tables exist (Skipping DDL, assuming pre-created or using Dashboard)...")
    # Note: To create tables from Python without RPC, we'd need a direct Postgres connection (psycopg2).
    # The Supabase client is REST-based.
    # We will proceed and catch errors.

def sync_regimes():
    print("\n🧠 [1/2] Syncing Regime Objects...")
    if not os.path.exists(REGIME_FILE):
        print("❌ No regime file found.")
        return

    regimes = []
    with open(REGIME_FILE, "r") as f:
        for line in f:
            try:
                r = json.loads(line)
                regimes.append({
                    "date": r['date'],
                    "regime_name": r['regime_name'],
                    "signature": r['signature'],
                    "historical_vibe": r.get('historical_vibe', ''),
                    "structural_reasoning": r.get('structural_reasoning', ''),
                    "risks": r.get('risks', []),
                    "upside": r.get('upside', [])
                })
            except:
                pass
                
    if regimes:
        # Batch upsert
        batch_size = 50
        for i in range(0, len(regimes), batch_size):
            batch = regimes[i:i+batch_size]
            try:
                supabase.table("intelligence_regimes").upsert(batch).execute()
                print(f"   ✅ Synced {len(batch)} regimes...")
            except Exception as e:
                print(f"   ⚠️ Error syncing regimes: {e}")
                print("   (Hint: Does the table 'intelligence_regimes' exist?)")
    else:
        print("   ⚠️ No regimes to sync.")

def sync_reports():
    print("\n📄 [2/2] Syncing Consensus Reports...")
    
    # Find all date directories
    date_dirs = glob.glob(os.path.join(REPORTS_DIR, "*"))
    
    reports_to_sync = []
    
    for d_path in date_dirs:
        if not os.path.isdir(d_path): continue
        
        date_str = os.path.basename(d_path)
        
        # 1. Institutional Report
        inst_path = os.path.join(d_path, "Institutional_Report.md")
        if os.path.exists(inst_path):
            with open(inst_path, "r") as f:
                content = f.read()
            reports_to_sync.append({
                "date": date_str,
                "type": "Institutional",
                "content": content
            })
            
        # 2. Personal Report
        pers_path = os.path.join(d_path, "Personal_Report.md")
        if os.path.exists(pers_path):
            with open(pers_path, "r") as f:
                content = f.read()
            reports_to_sync.append({
                "date": date_str,
                "type": "Personal",
                "content": content
            })
            
        # 3. Consensus Signal (Optional, maybe store in a separate column or table, 
        # but for now let's just attach it to the Institutional report if we want, 
        # or just ignore it. The user asked for reports.)
        # Let's try to update the consensus_signal field for the Institutional report if possible.
        
        sig_path = os.path.join(d_path, f"consensus_signal.json")
        # Or consensus_signal_{date}.json
        # Check both
        if not os.path.exists(sig_path):
            sig_path = os.path.join(d_path, f"consensus_signal_{date_str}.json")
            
        if os.path.exists(sig_path):
            try:
                with open(sig_path, "r") as f:
                    sig_json = json.load(f)
                # Find the Institutional report for this date and add signal
                for r in reports_to_sync:
                    if r['date'] == date_str and r['type'] == "Institutional":
                        r['consensus_signal'] = sig_json
            except:
                pass

    if reports_to_sync:
         # Batch upsert
        batch_size = 20
        for i in range(0, len(reports_to_sync), batch_size):
            batch = reports_to_sync[i:i+batch_size]
            try:
                supabase.table("intelligence_reports").upsert(batch).execute()
                print(f"   ✅ Synced {len(batch)} reports...")
            except Exception as e:
                print(f"   ⚠️ Error syncing reports: {e}")
                print("   (Hint: Does the table 'intelligence_reports' exist?)")
    else:
        print("   ⚠️ No reports to sync.")

def run_sync():
    print(f"🚀 REGIME ZERO INTELLIGENCE SYNC [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("="*60)
    
    sync_regimes()
    sync_reports()
    
    print("\n🎉 SYNC COMPLETE!")

if __name__ == "__main__":
    run_sync()
