"""
Telegram Alert System
"""
import urllib.request
import urllib.parse
import json
from typing import Optional
from datetime import datetime


class TelegramAlert:
    """Send alerts via Telegram bot"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def _send_request(self, method: str, params: dict) -> dict:
        """Send request to Telegram API"""
        url = f"{self.base_url}/{method}"
        data = urllib.parse.urlencode(params).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a text message"""
        result = self._send_request("sendMessage", {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        })
        return result.get("ok", False)

    def send_signal_alert(self, snapshot) -> bool:
        """Send signal alert with market snapshot"""
        emoji = {
            "STRONG_BUY": "🟢🟢🟢",
            "BUY": "🟢🟢",
            "LEAN_LONG": "🟢",
            "NEUTRAL": "⚪",
            "LEAN_SHORT": "🔴",
            "SELL": "🔴🔴",
            "STRONG_SELL": "🔴🔴🔴"
        }

        signals_text = "\n".join([
            f"  {'✅' if s.score > 0 else '🔴' if s.score < 0 else '⚪'} {s.name}: {s.value:.1f} ({s.description})"
            for s in snapshot.signals if s.score != 0
        ])

        text = f"""
<b>{emoji.get(snapshot.verdict, '⚪')} BTC Signal Alert</b>

<b>Price:</b> ${snapshot.price:,.0f}
<b>Score:</b> {snapshot.total_score:+d}
<b>Verdict:</b> {snapshot.verdict}

<b>Active Signals:</b>
{signals_text}

<b>Indicators:</b>
  RSI: {snapshot.rsi:.1f}
  BB Position: {snapshot.bb_position:.1f}%
  Fear & Greed: {snapshot.fng}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        return self.send_message(text)

    def send_trade_alert(self, trade_type: str, price: float, quantity: float,
                         score: int, verdict: str) -> bool:
        """Send trade execution alert"""
        emoji = "🟢" if trade_type == "BUY" else "🔴"

        text = f"""
<b>{emoji} Trade Executed</b>

<b>Type:</b> {trade_type}
<b>Price:</b> ${price:,.2f}
<b>Quantity:</b> {quantity:.6f} BTC
<b>Value:</b> ${price * quantity:,.2f}

<b>Signal:</b> Score {score:+d} ({verdict})

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        return self.send_message(text)

    def send_exit_alert(self, exit_type: str, entry_price: float, exit_price: float,
                        pnl: float, pnl_pct: float) -> bool:
        """Send position exit alert"""
        emoji = "💰" if pnl > 0 else "💸"

        text = f"""
<b>{emoji} Position Closed - {exit_type}</b>

<b>Entry:</b> ${entry_price:,.2f}
<b>Exit:</b> ${exit_price:,.2f}
<b>PnL:</b> ${pnl:,.2f} ({pnl_pct:+.2f}%)

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        return self.send_message(text)

    def send_daily_summary(self, stats: dict, balance: float) -> bool:
        """Send daily trading summary"""
        text = f"""
<b>📊 Daily Trading Summary</b>

<b>Balance:</b> ${balance:,.2f}
<b>Trades:</b> {stats['total']}
<b>Win Rate:</b> {stats['win_rate']:.1f}%
<b>Total PnL:</b> ${stats['total_pnl']:,.2f}
<b>Avg PnL:</b> {stats['avg_pnl_pct']:.2f}%

<i>{datetime.now().strftime('%Y-%m-%d')}</i>
"""
        return self.send_message(text)

    def send_error_alert(self, error: str) -> bool:
        """Send error alert"""
        text = f"""
<b>⚠️ Error Alert</b>

{error}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        return self.send_message(text)

    def send_kill_switch_alert(self, reason: str, balance: float) -> bool:
        """Send kill switch activation alert"""
        text = f"""
<b>🚨 KILL SWITCH ACTIVATED</b>

<b>Reason:</b> {reason}
<b>Current Balance:</b> ${balance:,.2f}

Trading has been halted. Manual intervention required.

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        return self.send_message(text)


class ConsoleAlert:
    """Fallback console alerter when Telegram not configured"""

    def send_message(self, text: str, **kwargs) -> bool:
        print(f"\n{'='*50}")
        print(text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
        print(f"{'='*50}\n")
        return True

    def send_signal_alert(self, snapshot) -> bool:
        print(f"\n[SIGNAL] {snapshot.verdict} | Score: {snapshot.total_score:+d} | ${snapshot.price:,.0f}")
        return True

    def send_trade_alert(self, *args, **kwargs) -> bool:
        print(f"[TRADE] {args}")
        return True

    def send_exit_alert(self, *args, **kwargs) -> bool:
        print(f"[EXIT] {args}")
        return True

    def send_daily_summary(self, *args, **kwargs) -> bool:
        print(f"[DAILY] {args}")
        return True

    def send_error_alert(self, error: str) -> bool:
        print(f"[ERROR] {error}")
        return True

    def send_kill_switch_alert(self, reason: str, balance: float) -> bool:
        print(f"[KILL SWITCH] {reason} | Balance: ${balance:,.2f}")
        return True
