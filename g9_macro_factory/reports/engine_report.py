from typing import List, Dict, Optional
from datetime import datetime
from g9_macro_factory.engine.charts.sparkline import get_market_stress_index, get_sparkline_data_last_30, generate_sparkline
from g9_macro_factory.engine.personalized.personal_diagnosis import get_watchlist_analysis_struct
from g9_macro_factory.engine.risk.unified_risk_score import calculate_unified_risk

def generate_g9_daily_report(macro_state: Dict, patterns: List[Dict], decisions: List[Dict], watchlist: Optional[List[str]] = None) -> str:
    """
    Generates a comprehensive G9 Intelligence Report in Markdown format.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # --- 1. Header Section ---
    report = []
    report.append(f"# 🧠 G9 ENGINE INTELLIGENCE REPORT")
    report.append(f"**Date**: {date_str} | **Version**: v2.0-Product")
    report.append("---")
    
    # Unified Risk Score
    # Assuming first decision has representative risk or calculate fresh
    # Ideally calculate fresh if not present
    unified_risk = None
    if decisions:
        unified_risk = decisions[0].get('unified_risk')
        
    if not unified_risk:
        # Fallback calculation
        unified_risk = calculate_unified_risk(macro_state, "AUTO", {})
        
    score = unified_risk.get('score', 0)
    label = unified_risk.get('label', 'Unknown')
    
    # Gauge Bar (ASCII)
    gauge_len = 20
    filled = int(score / 100 * gauge_len)
    gauge_bar = "█" * filled + "░" * (gauge_len - filled)
    
    report.append(f"### 🛡️ Unified Risk Score: {score:.1f}/100")
    report.append(f"`{gauge_bar}` **{label}**")
    
    # Sparkline
    spark_data = get_sparkline_data_last_30()
    if spark_data:
        spark_ascii = generate_sparkline(spark_data)
        report.append(f"**30-Day Stress Index**: `{spark_ascii}` (Trend: {spark_data[-1]:.1f})")
    
    regime = macro_state.get('regime', 'Unknown')
    report.append(f"**Market Regime**: `{regime}`")
    report.append("")
    
    # --- 2. Market Overview ---
    report.append("## 🌍 Market Overview")
    # Generate 3-line summary (Template based on VIX/Regime)
    vix = macro_state.get('VIX', {}).get('value', 0)
    summary_lines = []
    if vix > 25:
        summary_lines.append("- 🚨 **High Volatility**: Market fear is elevated (VIX > 25). Caution advised.")
    else:
        summary_lines.append("- ✅ **Stable Volatility**: Market conditions are relatively calm.")
        
    if regime == "LIQUIDITY_CRISIS":
        summary_lines.append("- 📉 **Liquidity Crisis**: Severe stress detected. Cash preservation is priority.")
    elif regime == "GROWTH_GOLDILOCKS":
        summary_lines.append("- 🚀 **Growth Phase**: Favorable conditions for risk assets.")
    else:
        summary_lines.append(f"- ⚖️ **{regime}**: Standard market operations.")
        
    summary_lines.append("- 💡 **G9 Insight**: Monitor pattern signals closely for directional changes.")
    report.extend(summary_lines)
    
    # Macro Table
    report.append("\n| Indicator | Value | Status |")
    report.append("| :--- | :--- | :--- |")
    for k, v in macro_state.items():
        if isinstance(v, dict) and 'value' in v:
            val = v['value']
            status = "Normal"
            if k == "VIX" and val > 20: status = "High"
            report.append(f"| {k} | {val:.2f} | {status} |")
    report.append("")
    
    # --- 3. Pattern Decision ---
    report.append("## 🧩 Pattern Decision")
    if not decisions:
        report.append("No actionable patterns detected.")
    else:
        for d in decisions:
            pid = d.get('pattern', 'Unknown')
            p_desc = "Pattern Description" # Placeholder or fetch
            report.append(f"- **{pid}**: {d.get('reason', '').split('|')[0].strip()}")
    report.append("")
    
    # --- 4. Final Action ---
    report.append("## 🎯 Final Action")
    for i, d in enumerate(decisions):
        action = d.get('action', 'HOLD')
        ticker = d.get('ticker', 'Unknown') # Assuming decision has ticker
        conf = d.get('confidence', 0.0)
        
        icon = "⚪"
        if action == "BUY": icon = "🟢"
        elif action == "SELL": icon = "🔴"
        elif action == "HOLD_CASH": icon = "🛡️"
        
        report.append(f"### {i+1}. {icon} {action} {ticker}")
        report.append(f"- **Confidence**: {conf:.2f}")
        
        # Overrides
        if "Momentum Override" in d.get('reason', ''):
            report.append(f"- **⚡ Momentum Override**: Triggered (Strong Trend detected).")
            
        if d.get('meta_rag_status') and "Warning" in d.get('meta_rag_status'):
             report.append(f"- **⚠️ Meta-RAG**: {d.get('meta_rag_status')}")
             
    report.append("")

    # --- 5. Risk Explainer ---
    report.append("## ⚠️ Risk Explainer")
    has_risk = False
    for d in decisions:
        if d.get('risk_explanation'):
            has_risk = True
            report.append(d.get('risk_explanation'))
            report.append("")
            
    if not has_risk:
        report.append("No significant risk overrides active.")
    report.append("")
    
    # --- 6. Watchlist Analyzer ---
    if watchlist:
        report.append("## 💼 Watchlist Analyzer")
        analysis = get_watchlist_analysis_struct(watchlist, decisions, macro_state)
        
        # Table
        report.append("| Ticker | Impact | Action | Meta-RAG |")
        report.append("| :--- | :--- | :--- | :--- |")
        for item in analysis:
            imp = item['impact_score']
            act = item['action_rec']
            meta = "Clean" if "Clean" in item['meta_rag_status'] else "⚠️ Warning"
            report.append(f"| **{item['ticker']}** | {imp:+.1f} | {act} | {meta} |")
            
        report.append("")
        
        # Detailed List
        for item in analysis:
            report.append(f"### {item['ticker']}")
            report.append(f"- **Impact**: {item['impact_score']:+.1f}")
            report.append(f"- **Pattern**: {item['pattern_id']} ({item['pattern_desc']})")
            report.append(f"- **Momentum**: {item['momentum_msg']}")
            if "Clean" not in item['meta_rag_status']:
                report.append(f"- **Meta-RAG**: {item['meta_rag_status']}")
            report.append(f"- **Recommendation**: {item['action_rec']}")
            report.append("")
            
    # --- 7. Footnotes ---
    report.append("---")
    report.append("### 📝 Footnotes")
    report.append("- **Data Source**: Yahoo Finance, Fred API")
    report.append("- **Disclaimer**: This report is for informational purposes only.")
    report.append("\n[✓ Report Renderer Complete]")
    
    return "\n".join(report)
