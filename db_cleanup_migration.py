import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.config import get_supabase_client
from no_session_injector import inject_no_session

def run_db_cleanup(start_date_str, end_date_str, country="GLOBAL"):
    print(f"🧹 Starting DB Cleanup Migration ({start_date_str} ~ {end_date_str})...")
    supabase = get_supabase_client()
    
    # Fetch Reports
    try:
        print("🔍 Scanning reports_daily for bad data...")
        
        # 1. Fetch all reports within the date range and country
        # reports_daily -> reports_daily
        res = supabase.table("reports_daily")\
            .select("id, date, country, report_json")\
            .eq("country", country)\
            .gte("date", start_date_str)\
            .lte("date", end_date_str)\
            .execute()
        
        reports = res.data or []
        
        print(f"📊 Found {len(reports)} reports. Checking quality...")
        
        bad_count = 0
        fixed_count = 0
        
        for r in reports:
            is_bad = False
            reason = ""
            
            # Check 1: Empty Content
            content = r.get("report_json")
            if not content:
                is_bad = True
                reason = "Empty Content"
            
            # Check 2: JSON Parse Error (if string)
            elif isinstance(content, str):
                try:
                    json.loads(content)
                except:
                    is_bad = True
                    reason = "JSON Parse Error"
            
            # Check 3: Missing Z-Score (Logic Check)
            # If it's a valid report, it should have z_score in content usually, 
            # but No-Session reports might not.
            # Let's just focus on "Empty" or "Error" for now.
            # The original code had this check, let's keep it if content is valid JSON
            else: # content is not empty and not a parse error
                try:
                    data = content if not isinstance(content, str) else json.loads(content)
                    z_score_focus = data.get('zscore_focus', {})
                    if not z_score_focus:
                        is_bad = True
                        reason = "Missing Z-Score Focus"
                    
                    # Also check if it's a "Mock" response or garbage
                    summary_lines = data.get('summary_3line', [])
                    if not summary_lines:
                        should_fix = True
                        reason = "Empty Summary"
                        
                except Exception as e:
                    should_fix = True
                    reason = f"JSON Parse Error: {e}"
            
            if should_fix:
                print(f"   ⚠️ Found Garbage Record: {date_str} ({reason}). Converting...")
                if inject_no_session(date_str, country, force=True):
                    fixed_count += 1
                    
        print(f"✅ DB Cleanup Complete. Fixed {fixed_count} records.")
        
    except Exception as e:
        print(f"❌ Cleanup Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DB Cleanup Migration")
    parser.add_argument("--start", type=str, required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--country", type=str, default="GLOBAL", help="Country Code")
    
    args = parser.parse_args()
    
    run_db_cleanup(args.start, args.end, args.country)
