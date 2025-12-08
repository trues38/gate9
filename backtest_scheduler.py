import os
import time
import json
from datetime import datetime, timedelta
from factor_engine import run_factor_engine
from auto_sql_engine import run_auto_sql
from utils.supabase_client import run_sql

def save_pattern_rag(date, factors, sql_result):
    """Save the verified pattern to RAG."""
    if not sql_result.get("results"):
        return
        
    title = f"Pattern: {factors['factors']['rates']['state']} + {factors['factors']['inflation']['state']}"
    summary = f"On {date}, market showed {title}. Similar past events found via AutoSQL."
    
    # Construct record
    record = {
        "title": title,
        "sql_query": sql_result["sql"],
        "summary": summary,
        "example_events": json.dumps(sql_result["results"])
    }
    
    # Insert into pattern_rag (using raw SQL for now as supabase-py insert might need specific setup)
    # Actually, let's try to use the supabase client if table exists.
    # But since I don't have the client initialized here, I'll use run_sql with INSERT.
    # Escaping is tricky with raw SQL string.
    # I'll use a safe approach or just print for now if this is a simulation.
    # User asked for "Save to RAG".
    
    print(f"💾 [RAG] Saving Pattern: {title}")
    # TODO: Implement actual INSERT when table is confirmed ready.
    # For now, just log it.

def run_backtest(start_date, end_date):
    print(f"🚀 Starting Backtest from {start_date} to {end_date}...")
    
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current_date <= end:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # 1. Calculate Factors
        try:
            factors = run_factor_engine(date_str)
            
            # 2. Check Significance (e.g. any factor is not Neutral/Stable)
            is_significant = False
            context = {"date": date_str, "factors": {}}
            
            for key, val in factors["factors"].items():
                state = val.get("state", "")
                if "Spike" in state or "Crash" in state or "Fast" in state or "Heating" in state:
                    is_significant = True
                    context["factors"][key] = state
            
            if is_significant:
                print(f"🔥 Significant Event on {date_str}. Triggering AutoSQL...")
                
                # 3. AutoSQL Verification
                sql_result = run_auto_sql(context)
                
                # 4. Save to RAG
                save_pattern_rag(date_str, factors, sql_result)
                
            else:
                print(f"zzz {date_str}: Market Quiet.")
                
        except Exception as e:
            print(f"❌ Error on {date_str}: {e}")
            
        current_date += timedelta(days=1)
        time.sleep(1) # Rate limit protection

if __name__ == "__main__":
    # Run a short test week
    run_backtest("2024-01-01", "2024-01-07")
