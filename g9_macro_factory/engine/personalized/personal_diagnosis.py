from typing import List, Dict

def get_watchlist_analysis_struct(watchlist: List[str], strategies: List[Dict], macro_state: Dict) -> List[Dict]:
    """
    Analyzes the user's watchlist and returns structured data for reporting.
    """
    if not watchlist:
        return []
        
    results = []
    regime = macro_state.get('regime', 'NEUTRAL')
    vix = macro_state.get('VIX', {}).get('value', 20.0)
    
    strat_map = {s['ticker']: s for s in strategies}
    
    for ticker in watchlist:
        # Defaults
        impact_score = 0.0
        pattern_id = "None"
        pattern_desc = "Macro Driven"
        news_summary = "No specific news detected."
        meta_rag_status = "Clean"
        action_rec = "HOLD"
        momentum_msg = "Neutral"
        
        # 1. Strategy Match
        if ticker in strat_map:
            strat = strat_map[ticker]
            pattern_id = strat.get('pattern_id', 'Unknown')
            pattern_desc = f"Pattern {pattern_id}"
            news_summary = strat.get('reason', 'No details.')
            
            if strat.get('meta_rag_status') and "Warning" in strat.get('meta_rag_status'):
                meta_rag_status = f"⚠️ {strat.get('meta_rag_status')}"
                if strat.get('risk_explanation'):
                    meta_rag_status += f" ({strat.get('risk_explanation').splitlines()[1]})"
            
            action = strat.get('action', 'SKIP')
            conf = strat.get('confidence', 0.0)
            
            if action == "SELL":
                impact_score = -15.0 * conf
                action_rec = "SELL / REDUCE"
            elif action == "BUY":
                impact_score = +15.0 * conf
                action_rec = "BUY / ACCUMULATE"
            elif action == "HOLD_CASH":
                impact_score = -10.0
                action_rec = "AVOID (Cash Preservation)"
            else:
                action_rec = "HOLD"
                
        # 2. Macro / Momentum Impact
        if vix > 25.0:
            momentum_msg = "Negative (High Volatility)"
            impact_score -= 5.0
        elif vix < 15.0:
            momentum_msg = "Positive (Stable)"
            impact_score += 2.0
            
        if regime == "LIQUIDITY_CRISIS":
            impact_score -= 20.0
            action_rec = "AVOID / HEDGE" if action_rec != "SELL" else "SELL IMMEDIATELY"
        elif regime == "GROWTH_GOLDILOCKS":
            impact_score += 5.0
            
        results.append({
            "ticker": ticker,
            "impact_score": impact_score,
            "pattern_id": pattern_id,
            "pattern_desc": pattern_desc,
            "momentum_msg": momentum_msg,
            "meta_rag_status": meta_rag_status,
            "news_summary": news_summary,
            "action_rec": action_rec
        })
        
    return results

def analyze_watchlist(watchlist: List[str], strategies: List[Dict], macro_state: Dict) -> str:
    """
    Analyzes the user's watchlist and returns a detailed personalized impact report.
    """
    data = get_watchlist_analysis_struct(watchlist, strategies, macro_state)
    if not data:
        return ""
        
    report_lines = ["\n[💼 Watchlist Analysis: Portfolio Impact]"]
    
    for item in data:
        block = []
        block.append(f"[{item['ticker']}] Impact Score: {item['impact_score']:+.1f}")
        block.append(f"   • Pattern: {item['pattern_id']} ({item['pattern_desc']})")
        block.append(f"   • Momentum: {item['momentum_msg']}")
        block.append(f"   • Meta-RAG: {item['meta_rag_status']}")
        block.append(f"   • News/Reason: \"{item['news_summary'][:60]}...\"")
        block.append(f"   👉 Recommendation: {item['action_rec']}")
        
        report_lines.append("\n".join(block))
        report_lines.append("") # Spacer
        
    return "\n".join(report_lines)
