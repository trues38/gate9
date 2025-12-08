import sys
import os
import json
import glob
from datetime import datetime

REPORTS_DIR = "regime_zero/reports/consensus"

def generate_attendance_log():
    print("📋 Generating Attendance Log...")
    
    dates = sorted([d for d in os.listdir(REPORTS_DIR) if os.path.isdir(os.path.join(REPORTS_DIR, d))])
    
    log_entries = []
    
    for date in dates:
        date_dir = os.path.join(REPORTS_DIR, date)
        models = [d for d in os.listdir(date_dir) if os.path.isdir(os.path.join(date_dir, d))]
        
        present = []
        absent = []
        
        # Expected models
        expected = ["Qwen14B", "DeepSeekV3", "GrokFast", "GPT-mini", "GeminiFlash"]
        
        for m in expected:
            if m in models:
                # Check if it was an error file
                if os.path.exists(os.path.join(date_dir, m, "ERROR.txt")):
                    absent.append(m)
                else:
                    present.append(m)
            else:
                absent.append(m)
                
        entry = f"## {date}\n"
        entry += f"- **Present**: {', '.join(present)}\n"
        if absent:
            entry += f"- **ABSENT**: {', '.join(absent)} (HR Intervention Required)\n"
        else:
            entry += "- **Perfect Attendance** ✅\n"
            
        log_entries.append(entry)
        
    # Save Log
    with open("regime_zero/company_docs/ATTENDANCE_LOG.md", "w") as f:
        f.write("# 📅 Regime Zero Capital – Attendance Log\n\n")
        f.write("\n".join(log_entries))
        
    print("✅ Attendance Log Updated: regime_zero/company_docs/ATTENDANCE_LOG.md")

if __name__ == "__main__":
    generate_attendance_log()
