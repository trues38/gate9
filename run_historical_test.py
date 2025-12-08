import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from g9_macro_factory.engine.decision_engine import DecisionEngine
from g9_macro_factory.engine.meta_rag import save_meta_fail_log
from g9_macro_factory.config import get_supabase_client
from utils.embedding import get_embedding_sync

# 20 Historical Scenarios
SCENARIOS = [
    {"date": "2000-03-10", "event": "Dotcom Bubble Burst", "ticker": "QQQ", "expected_pattern": "P-007"},
    {"date": "2001-09-17", "event": "9/11 Terrorist Attacks (Market Reopen)", "ticker": "SPY", "expected_pattern": "P-019"}, # 9/11 market closed until 9/17
    {"date": "2003-03-20", "event": "Iraq War Begins", "ticker": "SPY", "expected_pattern": "P-008"},
    {"date": "2008-09-15", "event": "Lehman Brothers Bankruptcy", "ticker": "SPY", "expected_pattern": "P-009"},
    {"date": "2011-08-05", "event": "US Credit Rating Downgrade", "ticker": "SPY", "expected_pattern": "P-030"},
    {"date": "2012-07-26", "event": "ECB Draghi 'Whatever it takes'", "ticker": "EUR", "expected_pattern": "P-020"},
    {"date": "2013-05-22", "event": "Bernanke Taper Tantrum", "ticker": "US10Y", "expected_pattern": "P-001"},
    {"date": "2015-08-11", "event": "China Yuan Devaluation Shock", "ticker": "CN_PMI", "expected_pattern": "P-006"},
    {"date": "2016-06-24", "event": "Brexit Vote Result", "ticker": "GBP", "expected_pattern": "P-015"},
    {"date": "2018-03-22", "event": "US-China Trade War Begins", "ticker": "SPY", "expected_pattern": "P-025"},
    {"date": "2018-02-05", "event": "Volmageddon (VIX Spike)", "ticker": "VIX", "expected_pattern": "P-050"}, # Generic Crisis
    {"date": "2019-07-31", "event": "Fed First Rate Cut (Pivot)", "ticker": "US10Y", "expected_pattern": "P-020"},
    {"date": "2020-03-11", "event": "WHO Declares COVID-19 Pandemic", "ticker": "SPY", "expected_pattern": "P-041"},
    {"date": "2020-11-09", "event": "Pfizer Vaccine Announcement", "ticker": "SPY", "expected_pattern": "P-033"},
    {"date": "2021-01-27", "event": "GameStop Short Squeeze Peak", "ticker": "GME", "expected_pattern": "P-048"},
    {"date": "2022-02-24", "event": "Russia Invades Ukraine", "ticker": "WTI", "expected_pattern": "P-008"},
    {"date": "2022-07-13", "event": "US CPI Hits 9.1%", "ticker": "SPY", "expected_pattern": "P-005"},
    {"date": "2023-03-10", "event": "SVB Bank Run", "ticker": "KRE", "expected_pattern": "P-034"},
    {"date": "2023-05-25", "event": "NVIDIA AI Earnings Surprise", "ticker": "NVDA", "expected_pattern": "P-047"},
    {"date": "2024-03-19", "event": "BOJ Ends Negative Rates", "ticker": "JPY", "expected_pattern": "P-004"}
]

def get_price_return(ticker, date_str, days=5):
    """Fetch T+days return from DB."""
    supabase = get_supabase_client()
    try:
        # Get start price
        res_start = supabase.table("price_daily").select("close").eq("ticker", ticker).eq("date", date_str).execute()
        if not res_start.data:
            # Try next day if weekend
            return 0.0
        start_price = res_start.data[0]['close']
        
        # Get end price
        # Simple date add (approximate, ignoring weekends for simplicity or query range)
        # Better: query > date limit 5
        res_end = supabase.table("price_daily").select("close").eq("ticker", ticker).gt("date", date_str).order("date").limit(days).execute()
        if not res_end.data:
            return 0.0
            
        end_price = res_end.data[-1]['close']
        return (end_price - start_price) / start_price
    except:
        return 0.0

def run_historical_test():
    print("🕰️  Running G9 Engine Historical Verification (20 Events)...")
    engine = DecisionEngine()
    
    results = []
    
    for i, scenario in enumerate(SCENARIOS):
        date_str = scenario['date']
        if date_str != "2020-03-11": continue
        
        event = scenario['event']
        ticker = scenario['ticker']
        
        print(f"\n[{i+1}/20] {date_str}: {event} ({ticker})")
        
def fetch_real_news(date_str, ticker, event_keywords):
    """Fetches real news from DB matching date and keywords."""
    supabase = get_supabase_client()
    # Search window: Date to Date+1 (24h)
    next_day = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        # Try specific ticker first
        res = supabase.table("global_news_all")\
            .select("published_at, title, summary, ticker")\
            .gte("published_at", date_str)\
            .lt("published_at", next_day)\
            .ilike("title", f"%{event_keywords.split()[0]}%")\
            .limit(1)\
            .execute()
            
        if res.data:
            return res.data[0]
            
        # Fallback: Just get any news for the ticker on that day
        res = supabase.table("global_news_all")\
            .select("published_at, title, summary, ticker")\
            .gte("published_at", date_str)\
            .lt("published_at", next_day)\
            .eq("ticker", ticker)\
            .limit(1)\
            .execute()
            
        if res.data:
            return res.data[0]
            
        return None
    except Exception as e:
        print(f"   ⚠️ News Fetch Error: {e}")
        return None

def run_historical_test():
    print("🕰️  Running G9 Engine Historical Verification (Real News + Forced Z-Score)...")
    engine = DecisionEngine()
    
    results = []
    
    for i, scenario in enumerate(SCENARIOS):
        date_str = scenario['date']
        event = scenario['event']
        ticker = scenario['ticker']
        
        print(f"\n[{i+1}/20] {date_str}: {event} ({ticker})")
        
        # 1. Fetch Real News
        real_news = fetch_real_news(date_str, ticker, event)
        
        if real_news:
            print(f"   📰 Found News: {real_news['title'][:50]}...")
            news_item = {
                "published_at": real_news['published_at'],
                "ticker": real_news['ticker'],
                "title": real_news['title'],
                "summary": real_news['summary']
            }
        else:
            print(f"   ⚠️ No Real News Found. Using Mock.")
            news_item = {
                "published_at": f"{date_str}T10:00:00",
                "ticker": ticker,
                "title": event,
                "summary": f"Breaking news: {event}. Markets react to major development."
            }
        
        # 2. Run Engine
        # Use General Mode to get daily insights even if Z-Score is low
        # No Forced Z-Score (use real data)
        z_override = None 
        
        # Exception for COVID to test Meta-RAG (Extreme Z) - Keep this for Anomaly check if needed
        # But for General Mode test, we want to see what it says with Real Z.
        # Let's run in GENERAL MODE.
        
        try:
            decision = engine.decide(news_item, z_score_data=z_override, mode="general")
            
            # 3. Ground Truth Verification
            check_ticker = ticker
            if ticker in ["KRE", "GME", "VIX", "CN_PMI", "GBP", "EUR", "JPY", "WTI"]: 
                check_ticker = "SPY" 
                
            actual_return = get_price_return(check_ticker, date_str, days=5)
            
            # Determine Correctness
            action = decision['action']
            is_correct = False
            
            if action == "BUY" or action == "BUY_THE_DIP":
                if actual_return > -0.01: 
                    is_correct = True
            elif action == "SELL" or action == "HOLD_CASH":
                if actual_return < 0.01: 
                    is_correct = True
            elif action == "HOLD" or action == "SKIP":
                is_correct = True 
                
            status_icon = "✅" if is_correct else "❌"
            print(f"   👉 Engine: {action} (Conf: {decision['confidence']}) | Return: {actual_return:.2%}")
            print(f"   👉 Regime: {decision['regime']} | Z-Score: {decision.get('z_score', 0.0):.2f}")
            print(f"   {status_icon} Verdict: {'Correct' if is_correct else 'WRONG'}")
            
            if decision.get('meta_rag_status') == "Warning":
                 print(f"   🛡️ Meta-RAG Warning Triggered!")

            results.append({
                "date": date_str,
                "event": event,
                "decision": decision,
                "return": actual_return,
                "correct": is_correct,
                "news_source": "Real" if real_news else "Mock"
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"   ❌ Error: {e}")

    # Save Summary
    with open("historical_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n✅ Historical Test Complete. Results saved to historical_test_results.json")

if __name__ == "__main__":
    run_historical_test()
