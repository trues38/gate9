import json
import os
import sys
from utils.supabase_client import run_sql

def add_unique_constraints():
    print("🚀 Adding Unique Constraints to Report Tables...")

    queries = [
        # Daily
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_unique ON daily_reports (date, country);",
        # Weekly
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_unique ON weekly_summaries (start_date, country);",
        # Monthly
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_unique ON monthly_summaries (month, country);",
        # Yearly
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_yearly_unique ON yearly_summaries (year, country);"
    ]
    
    for q in queries:
        print(f"Executing: {q}")
        try:
            res = run_sql(q)
            print(f"   Response: {res}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    print("✅ Unique Constraints Applied.")

if __name__ == "__main__":
    add_unique_constraints()
