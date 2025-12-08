import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client, TABLE_STRATEGY_MEMORY

def store_success(date_str, strategy, evaluation):
    """
    Stores successful strategy in DB.
    """
    supabase = get_supabase_client()
    
    payload = {
        "date": date_str,
        "ticker": strategy['ticker'],
        "action": strategy['action'],
        "reason": strategy.get('reason'),
        "confidence": strategy.get('confidence'),
        "entry_price": evaluation['entry_price'],
        "exit_price": evaluation['exit_price'],
        "return_pct": evaluation['return_pct']
    }
    
    try:
        supabase.table(TABLE_STRATEGY_MEMORY).insert(payload).execute()
        print(f"   💾 Stored success: {strategy['ticker']} ({evaluation['return_pct']:.2f}%)")
    except Exception as e:
        print(f"   ❌ Failed to store success: {e}")
