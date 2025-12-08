import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.backtest_engine.loader import retrieve_context
from g9_macro_factory.backtest_engine.rag_strategy import generate_strategy
from g9_macro_factory.backtest_engine.evaluator import evaluate_strategy
from g9_macro_factory.memory_core.success_store import store_success

def run_backtest_for_date(target_date_str, scores=None):
    print(f"\n🚀 Running Backtest for {target_date_str}")
    
    if scores is None:
        scores = {"z_score": 0.0, "impact_score": 0.0}
    
    # 1. Retrieve Context (Lookahead blocked)
    news = retrieve_context(target_date_str)
    if not news:
        print("   ⚠️ No news found. Skipping.")
        return None
        
    # 2. Generate Strategy
    strategies = generate_strategy(news, scores)
    if not strategies:
        print("   ⚠️ No strategy generated. Skipping.")
        return None
        
    # For simplicity, take the first one
    strategy = strategies[0]
    
    # 3. Evaluate
    evaluation = evaluate_strategy(target_date_str, strategy['ticker'], strategy['action'])
    # Note: If evaluation fails (no price), we can't save full intelligence with returns.
    # But we should save what we have? Or skip?
    # User said "Result" is part of the table.
    # If no price, we can't verify.
    
    if not evaluation:
        print("   ⚠️ Evaluation failed (missing price data).")
        return None
        
    print(f"   📈 Result: {evaluation['return_pct']:.2f}% (Success: {evaluation['is_success']})")
    
    # 4. Store Intelligence (Memory Palace)
    from g9_macro_factory.memory_core.intelligence_store import save_intelligence_packet
    
    packet = {
        "target_date": target_date_str,
        "ticker": strategy['ticker'],
        "sector": "Unknown", # We don't have sector info yet, maybe from Ticker Map?
        "z_score": scores.get('z_score', 0.0),
        "impact_score": scores.get('impact_score', 0.0),
        "macro_env": strategy.get('macro_state', {}),
        "pattern_id": strategy.get('pattern_id'),
        "strategy_type": strategy.get('action'), # BUY/SELL
        "confidence_score": strategy.get('confidence', 0.0),
        "final_logic": strategy.get('reason'),
        "return_3d": evaluation.get('return_pct', 0.0), # Assuming 7d is same for now or we need eval to return both
        "return_7d": evaluation.get('return_pct', 0.0),
        "success_flag": evaluation['is_success']
    }
    save_intelligence_packet(packet)

    # 5. Store Success (Legacy)
    if evaluation['is_success']:
        store_success(target_date_str, strategy, evaluation)
        
    return {
        "date": target_date_str,
        "ticker": strategy['ticker'],
        "action": strategy['action'],
        "return_pct": evaluation['return_pct'],
        "is_success": evaluation['is_success']
    }
