import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client, TABLE_PRICE_DAILY, SUCCESS_THRESHOLD_PCT

def evaluate_strategy(date_str, ticker, action):
    """
    Evaluates the strategy return over 7 days.
    Returns: {return_pct, is_success, entry_price, exit_price}
    """
    supabase = get_supabase_client()
    
    start_date = datetime.fromisoformat(date_str).date()
    end_date = start_date + timedelta(days=7)
    
    # Fetch prices
    res = supabase.table(TABLE_PRICE_DAILY)\
        .select("date, close")\
        .eq("ticker", ticker)\
        .gte("date", start_date.isoformat())\
        .lte("date", end_date.isoformat())\
        .order("date")\
        .execute()
        
    prices = res.data
    
    if not prices:
        print(f"   ⚠️ No price data for {ticker} starting {date_str}.")
        return None
        
    # Entry price is the first available price ON or AFTER the decision date.
    # Ideally, if decision is made on date_str (using data BEFORE date_str), 
    # we enter on date_str (Open/Close).
    # Let's assume we enter at Close of the first available day.
    
    entry_price = float(prices[0]['close'])
    exit_price = float(prices[-1]['close'])
    
    if action == "BUY":
        return_pct = ((exit_price - entry_price) / entry_price) * 100
    elif action == "SELL":
        return_pct = ((entry_price - exit_price) / entry_price) * 100
    else:
        return_pct = 0.0
        
    is_success = return_pct >= SUCCESS_THRESHOLD_PCT
    
    # Special case: If SELL and return is positive, it means price dropped.
    # Logic above: (Entry - Exit) / Entry.
    # If Entry=100, Exit=90. (100-90)/100 = 10%. Correct.
    
    return {
        "return_pct": return_pct,
        "is_success": is_success,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "days_held": len(prices)
    }
