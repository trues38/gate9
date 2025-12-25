
import os
import shutil
import datetime

EXPORT_DIR = "g9_core_export"

CORE_ASSETS = [
    # Manifesto & Logic
    {"src": "system_manifesto.md", "dst": "system_manifesto.md"},
    {"src": "reports/final_pattern_summary.md", "dst": "REPORTS/final_pattern_summary.md"},
    {"src": "reports/dead_zones.md", "dst": "REPORTS/dead_zones.md"},
    {"src": "reports/track2_lab_results.md", "dst": "REPORTS/lab_evidence.md"},
    
    # Critical Data
    {"src": "processed/nba_regime_index_v1.json", "dst": "DATA/nba_regime_index.json"},
    {"src": "processed/regime_directional_dataset.csv", "dst": "DATA/regime_directional_dataset.csv"},
    
    # Factory Scripts
    {"src": "scripts/generate_sellable_report.py", "dst": "FACTORY/daily_report_gen.py"},
    {"src": "scripts/run_track1_scorecard.py", "dst": "FACTORY/scorecard_engine.py"},
]

def pack_for_exodus():
    print(f"📦 Operation Exodus: Packing G9 Core to {EXPORT_DIR}...")
    
    if os.path.exists(EXPORT_DIR):
        shutil.rmtree(EXPORT_DIR)
    os.makedirs(EXPORT_DIR)
    os.makedirs(os.path.join(EXPORT_DIR, "DATA"))
    os.makedirs(os.path.join(EXPORT_DIR, "REPORTS"))
    os.makedirs(os.path.join(EXPORT_DIR, "FACTORY"))
    
    for item in CORE_ASSETS:
        src_path = item['src']
        dst_path = os.path.join(EXPORT_DIR, item['dst'])
        
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)
            print(f"  ✅ Copied {src_path} -> {dst_path}")
        else:
            print(f"  ⚠️ Warning: {src_path} NOT FOUND. Skipping.")
            
    # Create README_INSTALL.md
    readme_content = f"""# 🦅 G9 Engine (Lite Version)
**Deployment Package | Generated: {datetime.date.today()}**

## 1. Introduction
This is the core export of the G9 Anti-Gravity Engine.
It contains the essential Logic, Data, and Factory scripts to run the business.
The heavy research infrastructure has been stripped away.

## 2. Directory Structure
- **DATA/**: The Gold Standard Dataset (17 Years of Regime).
- **REPORTS/**: The Logic Manifesto and Evidence.
- **FACTORY/**: Python scripts to generate daily products.
- **system_manifesto.md**: The Constitution.

## 3. How to Run the Business
1. **Daily Morning Report**:
   - Run `python3 FACTORY/daily_report_gen.py`
   - This produces the "Morning Report" for customers.
   
2. **Scorecard Analysis**:
   - Run `python3 FACTORY/scorecard_engine.py`
   - This runs the Logic Core (Base Prob + Dead Zone Auto-Fade).

## 4. Maintenance
- To update the engine, ingest new games into `DATA/regime_directional_dataset.csv`.
- Re-run `scorecard_engine.py` to tune the logic.

> "Market is Efficient. Shape is Not."
"""

    with open(os.path.join(EXPORT_DIR, "README_INSTALL.md"), "w") as f:
        f.write(readme_content)
        
    print("✅ Exodus Pack Complete. The Engine is ready to move.")

if __name__ == "__main__":
    pack_for_exodus()
