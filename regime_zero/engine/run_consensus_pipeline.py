import sys
import os
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.engine.find_historical_twin import find_twin
from regime_zero.engine.junior_analysts import run_junior_analysis
from regime_zero.engine.meta_reviewer import run_meta_review
from regime_zero.engine.senior_cio import generate_final_reports

REPORTS_DIR = "regime_zero/reports/consensus"
CANDIDATES_FILE = "regime_zero/engine/twin_candidates.json"

def run_pipeline(target_date):
    print(f"\n🚀 STARTING CONSENSUS PIPELINE FOR {target_date}")
    print("="*50)
    
    # 0. Ensure Reports Dir Exists
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # 1. Twin Search (Data Layer)
    print("\n[STEP 1] 🔍 Finding Historical Twins...")
    try:
        # Redirect stdout to suppress verbose output if needed, or just let it print
        find_twin(target_date)
    except Exception as e:
        print(f"❌ Twin Search Failed: {e}")
        return

    # Load Candidates
    if not os.path.exists(CANDIDATES_FILE):
        print("❌ No candidates file found.")
        return
        
    with open(CANDIDATES_FILE, "r") as f:
        candidates = json.load(f)
    
    # Prepare Data Context
    data_context = {
        "target_date": target_date,
        "top_5_twins": candidates[:5]
    }

    # 2. Junior Analysts (Layer 1)
    print("\n[STEP 2] 🤖 Junior Analysts Working...")
    junior_outputs = run_junior_analysis(data_context)
    
    # Create Date Directory
    date_dir = os.path.join(REPORTS_DIR, target_date)
    os.makedirs(date_dir, exist_ok=True)

    # Save Junior Outputs (Structured)
    for model_name, content in junior_outputs.items():
        model_dir = os.path.join(date_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        if content:
            # Save Report
            with open(os.path.join(model_dir, "report.md"), "w") as f:
                f.write(content.get("report", "No Report"))
            
            # Save Self-Audit
            with open(os.path.join(model_dir, "self_audit.md"), "w") as f:
                f.write(content.get("self_audit", "No Audit"))
                
            # Save Raw JSON
            with open(os.path.join(model_dir, "raw_output.json"), "w") as f:
                json.dump(content, f, indent=2)
        else:
            # Save Error Note
            with open(os.path.join(model_dir, "ERROR.txt"), "w") as f:
                f.write("Model failed to generate output.")

    # 3. Meta Reviewer (Layer 2)
    print("\n[STEP 3] ⚖️  Meta Reviewer Synthesizing...")
    consensus_json = run_meta_review(junior_outputs)
    
    if not consensus_json:
        print("❌ Meta Review Failed. Aborting.")
        return

    # Save Consensus JSON
    with open(os.path.join(date_dir, "consensus_signal.json"), "w") as f:
        json.dump(consensus_json, f, indent=2)
    
    print(f"✅ Consensus Signal: {json.dumps(consensus_json['final_consensus'], indent=2)}")

    # 4. Senior CIO (Layer 3)
    print("\n[STEP 4] 👔 Senior CIO Writing Final Reports...")
    final_reports = generate_final_reports(consensus_json, target_date)
    
    if final_reports:
        # Save Institutional
        inst_path = os.path.join(date_dir, "Institutional_Report.md")
        with open(inst_path, "w") as f:
            f.write(final_reports['institutional'])
        print(f"✅ Saved Institutional Report: {inst_path}")
        
        # Save Personal
        pers_path = os.path.join(date_dir, "Personal_Report.md")
        with open(pers_path, "w") as f:
            f.write(final_reports['personal'])
        print(f"✅ Saved Personal Report: {pers_path}")

    print("\n🎉 PIPELINE COMPLETE!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"), help="Target Date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    run_pipeline(args.date)
