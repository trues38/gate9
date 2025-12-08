from typing import List, Dict
from datetime import datetime
from g9_macro_factory.engine.charts.sparkline import get_market_stress_index
from g9_macro_factory.engine.personalized.personal_diagnosis import analyze_watchlist

def generate_daily_report(strategies: List[Dict], macro_state: Dict, watchlist: List[str] = None) -> str:
    """
    Generates the full G9 Daily Intelligence Report.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    report = []
    report.append(f"==========================================")
    report.append(f" G9 ENGINE DAILY INTELLIGENCE ({date_str})")
    report.append(f"==========================================\n")
    
    # 1. Sparkline (Market Stress)
    report.append(get_market_stress_index(30))
    report.append("")
    
    # [v2.0] Unified Risk Score (from first strategy or macro)
    # Since risk score is calculated per decision, we can take the max or first one.
    # Ideally, it should be calculated once per day.
    # Let's assume the first strategy contains the representative risk score.
    unified_risk = None
    if strategies:
        unified_risk = strategies[0].get('unified_risk')
        
    if unified_risk:
        score = unified_risk.get('score', 0)
        label = unified_risk.get('label', 'Unknown')
        action = unified_risk.get('action', '')
        report.append(f"[🛡️ Unified Risk Score: {score}/100 ({label})]")
        report.append(f"   Action: {action}")
        report.append("")
    
    # 2. Macro Regime
    regime = macro_state.get('regime', 'Unknown')
    report.append(f"[🌍 Market Regime: {regime}]")
    if 'regime_desc' in macro_state:
        report.append(f"{macro_state['regime_desc']}")
    report.append("")
    
    # 3. Top Strategies
    report.append("[🚀 Top Trading Strategies]")
    if not strategies:
        report.append("No significant opportunities detected today.")
    else:
        for i, strat in enumerate(strategies):
            action = strat.get('action', 'SKIP')
            ticker = strat.get('ticker', 'UNKNOWN')
            reason = strat.get('reason', 'No reason provided.')
            conf = strat.get('confidence', 0.0)
            
            icon = "⚪"
            if action == "BUY": icon = "🟢"
            elif action == "SELL": icon = "🔴"
            elif action == "HOLD_CASH": icon = "🛡️"
            
            report.append(f"{i+1}. {icon} {action} {ticker} (Conf: {conf:.2f})")
            report.append(f"   Reason: {reason}")
            
            # Meta-RAG Warning & Risk Explanation
            if strat.get('meta_rag_status') and "Warning" in strat.get('meta_rag_status'):
                # report.append(f"   ⚠️ Meta-RAG Warning: {strat.get('meta_rag_warning_document', '').splitlines()[0]}")
                # Use Risk Explainer instead
                risk_exp = strat.get('risk_explanation', '')
                if risk_exp:
                    report.append(f"\n{risk_exp}")
                else:
                    report.append(f"   ⚠️ Meta-RAG Warning: {strat.get('meta_rag_warning_document', '').splitlines()[0]}")
            report.append("")
            
    # 4. Personalized Diagnosis
    if watchlist:
        diag = analyze_watchlist(watchlist, strategies, macro_state)
        report.append(diag)
        
    report.append("\n==========================================")
    report.append(" End of Report")
    report.append("==========================================")
    
    return "\n".join(report)
