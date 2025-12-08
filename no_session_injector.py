import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.config import get_supabase_client
from g9_macro_factory.utils.holiday_utils import get_no_session_json, is_trading_day

def inject_no_session(date_str, country="GLOBAL", force=False):
    """
    Injects a No-Session JSON for the given date if it is a holiday/weekend.
    If force=True, injects regardless of holiday status (used for cleanup).
class NoSessionInjector:
    def __init__(self):
        self.supabase = get_supabase_client()

    def inject(self, date_str, country, force=False):
        # 1. Check if report exists
        if not force:
            existing = self.supabase.table("reports_daily")\
                .select("id")\
                .eq("date", date_str)\
                .eq("country", country)\
                .execute()
            if existing.data:
                print(f"   ℹ️ Report already exists for {date_str} ({country}). Skipping.")
                return

        # 2. Prepare No-Session Data
        no_session_data = get_no_session_json(date_str)
        
        # 3. Save to DB (reports_daily)
        payload = {
            "date": date_str,
            "country": country,
            "report_json": json.dumps(no_session_data),
            "created_at": "now()"
        }
        
        try:
            self.supabase.table("reports_daily").upsert(payload, on_conflict="date, country").execute()
            print(f"   ✅ Injected No-Session for {date_str} ({country})")
            
            # Also update preprocess_daily if needed?
            # The user said "Preprocess Layer... Report Layer..."
            # Usually we want consistency. If we inject a report, we might want to ensure preprocess_daily also has a record?
            # But preprocess_daily has different schema (flattened).
            # DailyPreprocessor handles No-Session injection into preprocess_daily.
            # This script seems to be for the Report Layer specifically.
            # I will stick to reports_daily here.
            
        except Exception as e:
            print(f"   ❌ Injection Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="No-Session JSON Injector")
    parser.add_argument("--date", type=str, required=True, help="Date (YYYY-MM-DD)")
    parser.add_argument("--country", type=str, default="GLOBAL", help="Country Code")
    parser.add_argument("--force", action="store_true", help="Force injection even if trading day")
    
    args = parser.parse_args()
    
    inject_no_session(args.date, args.country, args.force)
