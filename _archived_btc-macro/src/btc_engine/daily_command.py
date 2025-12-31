"""
BTC Daily Command Generator

통합 출력: Relative Engine + Law + Sniper

이 포맷이 그대로 유료 SaaS 알림이 된다.
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

from datetime import datetime
from btc_engine.relative_engine.btc_relative_engine import BTCRelativeEngine
from btc_engine.sniper.l3_micro_sniper import L3MicroSniper
from btc_engine.laws.etf_accumulation import ETFAccumulationLaw


def generate_daily_command() -> str:
    """Generate unified daily command"""

    today = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Initialize components
    relative = BTCRelativeEngine()
    sniper = L3MicroSniper()
    law = ETFAccumulationLaw()

    # Get data
    scores = relative.calculate_scores()
    sniper_signal = sniper.get_entry_signal()
    law_signal = law.get_current_signal()

    # Rankings
    long_asset = scores[0]
    avoid_assets = [s for s in scores if s.rank >= 3]

    lines = []

    # Header
    lines.append("╔" + "═" * 56 + "╗")
    lines.append("║" + f" BTC RELATIVE COMMAND - {today}".center(56) + "║")
    lines.append("╠" + "═" * 56 + "╣")

    # Main Command
    lines.append("║" + "".center(56) + "║")
    lines.append("║" + f"  1️⃣  LONG:       {long_asset.name}".ljust(56) + "║")

    if len(avoid_assets) > 0:
        lines.append("║" + f"  2️⃣  AVOID:      {avoid_assets[0].name}".ljust(56) + "║")
    if len(avoid_assets) > 1:
        lines.append("║" + f"  3️⃣  SHORT BIAS: {avoid_assets[1].name}".ljust(56) + "║")

    lines.append("║" + "".center(56) + "║")
    lines.append("╠" + "═" * 56 + "╣")

    # Law Status
    law_active = sniper_signal.law_active
    law_icon = "🟢 ACTIVE" if law_active else "⚪ INACTIVE"
    lines.append("║" + f"  [LAW] ETF_ACCUMULATION: {law_icon}".ljust(56) + "║")

    # Sniper Status
    rsi_ok = sniper_signal.rsi_1h < 45
    vwap_ok = sniper_signal.price_vs_vwap in ['breakout', 'above']

    rsi_icon = "🟢" if rsi_ok else "⚪"
    vwap_icon = "🟢" if sniper_signal.price_vs_vwap == 'breakout' else ("🟡" if vwap_ok else "⚪")

    lines.append("║" + f"  [RSI] 1H: {sniper_signal.rsi_1h:.1f} {rsi_icon}  [VWAP] {sniper_signal.price_vs_vwap.upper()} {vwap_icon}".ljust(56) + "║")

    lines.append("║" + "".center(56) + "║")
    lines.append("╠" + "═" * 56 + "╣")

    # Entry Signal
    if sniper_signal.entry_signal:
        lines.append("║" + "  🎯 ENTRY: EXECUTE NOW".ljust(56) + "║")
        lines.append("║" + f"     BTC @ ${sniper_signal.price:,.0f}".ljust(56) + "║")
        lines.append("║" + "     TP: +7% / SL: -5% / TIME: 10d".ljust(56) + "║")
    elif law_active:
        lines.append("║" + "  ⏳ ENTRY: WAIT FOR SNIPER".ljust(56) + "║")
        lines.append("║" + f"     Need: RSI<45 (now {sniper_signal.rsi_1h:.1f})".ljust(56) + "║")
    else:
        lines.append("║" + "  ⏸️  ENTRY: STANDBY".ljust(56) + "║")
        lines.append("║" + "     Waiting for ETF Accumulation signal".ljust(56) + "║")

    lines.append("║" + "".center(56) + "║")
    lines.append("╠" + "═" * 56 + "╣")

    # Scores
    lines.append("║" + "  RELATIVE SCORES:".ljust(56) + "║")
    for s in scores:
        score_line = f"    {s.rank}. {s.name:<6} {s.total_score:+.2f} ({s.signal})"
        lines.append("║" + score_line.ljust(56) + "║")

    lines.append("║" + "".center(56) + "║")
    lines.append("╠" + "═" * 56 + "╣")

    # Reason
    lines.append("║" + "  REASON:".ljust(56) + "║")
    lines.append("║" + f"    • ETF Sens: {long_asset.etf_sensitivity:+.1f}".ljust(56) + "║")
    lines.append("║" + f"    • Lag Adv:  {long_asset.lag_advantage:+.1f}% vs BTC".ljust(56) + "║")
    lines.append("║" + f"    • Heat:     {long_asset.overheat:+.1f} (RSI-based)".ljust(56) + "║")

    lines.append("║" + "".center(56) + "║")
    lines.append("╚" + "═" * 56 + "╝")

    return "\n".join(lines)


def main():
    print(generate_daily_command())


if __name__ == "__main__":
    main()
