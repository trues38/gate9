"""
ETF Law Real-Time Alert System

신호: IBIT Vol > 1.3x (10일 평균) + BTC 일봉 -2% 이상 하락
알림: Console, File, Webhook (Telegram/Discord/Slack)

Usage:
    python etf_law_monitor.py              # 1회 체크
    python etf_law_monitor.py --daemon     # 데몬 모드 (15분마다)
    python etf_law_monitor.py --test       # 테스트 알림
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

import yfinance as yf
import pandas as pd

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ALERT_LOG_DIR = PROJECT_ROOT / "logs" / "alerts"
STATE_FILE = PROJECT_ROOT / "logs" / "alert_state.json"


@dataclass
class MarketState:
    timestamp: str
    btc_price: float
    btc_ret_1d: float
    ibit_volume: int
    ibit_vol_ratio: float
    law_active: bool
    signal_strength: str  # 'STRONG', 'MODERATE', 'WEAK', 'NONE'


@dataclass
class Alert:
    timestamp: str
    alert_type: str  # 'ENTRY', 'EXIT', 'WARNING'
    title: str
    message: str
    market_state: MarketState


class AlertChannel:
    """Base class for alert channels"""

    def send(self, alert: Alert) -> bool:
        raise NotImplementedError


class ConsoleAlert(AlertChannel):
    """Console output"""

    def send(self, alert: Alert) -> bool:
        print("\n" + "=" * 60)
        print(f"🚨 [{alert.alert_type}] {alert.title}")
        print("=" * 60)
        print(f"Time: {alert.timestamp}")
        print(f"\n{alert.message}")
        print("\n" + "-" * 60)
        print(f"BTC: ${alert.market_state.btc_price:,.0f} ({alert.market_state.btc_ret_1d*100:+.1f}%)")
        print(f"IBIT Vol: {alert.market_state.ibit_vol_ratio:.2f}x avg")
        print(f"Signal: {alert.market_state.signal_strength}")
        print("=" * 60 + "\n")
        return True


class FileAlert(AlertChannel):
    """File logging"""

    def __init__(self, log_dir: Path = ALERT_LOG_DIR):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def send(self, alert: Alert) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"alerts_{today}.jsonl"

        with open(log_file, "a") as f:
            f.write(json.dumps(asdict(alert), default=str) + "\n")

        return True


class WebhookAlert(AlertChannel):
    """Webhook for Telegram/Discord/Slack"""

    def __init__(self, webhook_url: str, platform: str = "discord"):
        self.webhook_url = webhook_url
        self.platform = platform

    def _format_discord(self, alert: Alert) -> Dict:
        color = {
            'ENTRY': 0x00FF00,  # Green
            'EXIT': 0xFF0000,   # Red
            'WARNING': 0xFFFF00  # Yellow
        }.get(alert.alert_type, 0x808080)

        return {
            "embeds": [{
                "title": f"🚨 {alert.title}",
                "description": alert.message,
                "color": color,
                "fields": [
                    {"name": "BTC Price", "value": f"${alert.market_state.btc_price:,.0f}", "inline": True},
                    {"name": "BTC 1D", "value": f"{alert.market_state.btc_ret_1d*100:+.1f}%", "inline": True},
                    {"name": "IBIT Vol", "value": f"{alert.market_state.ibit_vol_ratio:.2f}x", "inline": True},
                    {"name": "Signal", "value": alert.market_state.signal_strength, "inline": True},
                ],
                "timestamp": alert.timestamp
            }]
        }

    def _format_telegram(self, alert: Alert) -> Dict:
        emoji = {'ENTRY': '🟢', 'EXIT': '🔴', 'WARNING': '🟡'}.get(alert.alert_type, '⚪')

        text = f"""
{emoji} *{alert.title}*

{alert.message}

📊 *Market State*
• BTC: ${alert.market_state.btc_price:,.0f} ({alert.market_state.btc_ret_1d*100:+.1f}%)
• IBIT Vol: {alert.market_state.ibit_vol_ratio:.2f}x avg
• Signal: {alert.market_state.signal_strength}

🕐 {alert.timestamp}
"""
        return {"text": text, "parse_mode": "Markdown"}

    def _format_slack(self, alert: Alert) -> Dict:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚨 {alert.title}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": alert.message}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*BTC*\n${alert.market_state.btc_price:,.0f}"},
                        {"type": "mrkdwn", "text": f"*1D Change*\n{alert.market_state.btc_ret_1d*100:+.1f}%"},
                        {"type": "mrkdwn", "text": f"*IBIT Vol*\n{alert.market_state.ibit_vol_ratio:.2f}x"},
                        {"type": "mrkdwn", "text": f"*Signal*\n{alert.market_state.signal_strength}"},
                    ]
                }
            ]
        }

    def send(self, alert: Alert) -> bool:
        if not self.webhook_url:
            return False

        try:
            if self.platform == "discord":
                payload = self._format_discord(alert)
            elif self.platform == "telegram":
                payload = self._format_telegram(alert)
            elif self.platform == "slack":
                payload = self._format_slack(alert)
            else:
                payload = {"text": f"{alert.title}: {alert.message}"}

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Webhook error: {e}")
            return False


class ETFLawMonitor:
    """ETF Accumulation Law Monitor"""

    # Signal thresholds
    VOL_THRESHOLD = 1.3
    DOWN_THRESHOLD = -0.02

    # Strong signal thresholds
    STRONG_VOL = 2.0
    STRONG_DOWN = -0.05

    def __init__(self, channels: List[AlertChannel] = None):
        self.channels = channels or [ConsoleAlert(), FileAlert()]
        self.state_file = STATE_FILE
        self.last_alert_date = self._load_state()

    def _load_state(self) -> Optional[str]:
        """Load last alert date to avoid duplicates"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                return state.get("last_alert_date")
        return None

    def _save_state(self, alert_date: str):
        """Save state"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump({"last_alert_date": alert_date, "updated": datetime.now().isoformat()}, f)

    def fetch_market_data(self) -> Optional[MarketState]:
        """Fetch current market data"""
        try:
            # BTC data
            btc = yf.download("BTC-USD", period="15d", progress=False)
            if isinstance(btc.columns, pd.MultiIndex):
                btc.columns = btc.columns.get_level_values(0)

            # IBIT data
            ibit = yf.download("IBIT", period="15d", progress=False)
            if isinstance(ibit.columns, pd.MultiIndex):
                ibit.columns = ibit.columns.get_level_values(0)

            if len(btc) < 2 or len(ibit) < 10:
                return None

            # Current values
            btc_price = btc["Close"].iloc[-1]
            btc_ret_1d = (btc["Close"].iloc[-1] - btc["Close"].iloc[-2]) / btc["Close"].iloc[-2]

            ibit_vol = ibit["Volume"].iloc[-1]
            ibit_vol_ma10 = ibit["Volume"].rolling(10).mean().iloc[-1]
            ibit_vol_ratio = ibit_vol / ibit_vol_ma10

            # Law check
            law_active = ibit_vol_ratio > self.VOL_THRESHOLD and btc_ret_1d < self.DOWN_THRESHOLD

            # Signal strength
            if law_active:
                if ibit_vol_ratio > self.STRONG_VOL or btc_ret_1d < self.STRONG_DOWN:
                    strength = "STRONG"
                elif ibit_vol_ratio > 1.5 or btc_ret_1d < -0.03:
                    strength = "MODERATE"
                else:
                    strength = "WEAK"
            else:
                strength = "NONE"

            return MarketState(
                timestamp=datetime.now().isoformat(),
                btc_price=btc_price,
                btc_ret_1d=btc_ret_1d,
                ibit_volume=int(ibit_vol),
                ibit_vol_ratio=ibit_vol_ratio,
                law_active=law_active,
                signal_strength=strength
            )

        except Exception as e:
            print(f"Data fetch error: {e}")
            return None

    def create_alert(self, state: MarketState) -> Alert:
        """Create alert from market state"""
        if state.law_active:
            title = "ETF ACCUMULATION SIGNAL DETECTED"
            message = f"""
🎯 ENTRY SIGNAL ACTIVE

기관 ETF 딥 매수 감지!
• IBIT 볼륨: {state.ibit_vol_ratio:.1f}x (평균 대비)
• BTC 하락: {state.btc_ret_1d*100:.1f}%

📋 ACTION:
• Direction: LONG BTC
• Entry: 현재가 ${state.btc_price:,.0f}
• TP: +7% (${state.btc_price * 1.07:,.0f})
• SL: -5% (${state.btc_price * 0.95:,.0f})
• Time: Max 10일
            """.strip()
            alert_type = "ENTRY"
        else:
            title = "MARKET STATUS UPDATE"
            message = f"No active signal. Vol={state.ibit_vol_ratio:.2f}x, BTC={state.btc_ret_1d*100:+.1f}%"
            alert_type = "WARNING"

        return Alert(
            timestamp=state.timestamp,
            alert_type=alert_type,
            title=title,
            message=message,
            market_state=state
        )

    def send_alert(self, alert: Alert):
        """Send alert through all channels"""
        for channel in self.channels:
            try:
                channel.send(alert)
            except Exception as e:
                print(f"Alert channel error: {e}")

    def check_and_alert(self, force: bool = False) -> bool:
        """Main check routine"""
        state = self.fetch_market_data()

        if state is None:
            print("Failed to fetch market data")
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        # Only alert once per day unless forced
        if state.law_active:
            if self.last_alert_date == today and not force:
                print(f"Already alerted today ({today}). Use --force to resend.")
                return False

            alert = self.create_alert(state)
            self.send_alert(alert)
            self._save_state(today)
            self.last_alert_date = today
            return True
        else:
            # Print status but don't alert
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No signal - Vol={state.ibit_vol_ratio:.2f}x, BTC={state.btc_ret_1d*100:+.1f}%")
            return False

    def run_daemon(self, interval_minutes: int = 15):
        """Run as daemon, checking every N minutes"""
        print(f"Starting ETF Law Monitor daemon (interval: {interval_minutes}min)")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                self.check_and_alert()
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nStopping daemon...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)  # Wait 1 min on error


def main():
    parser = argparse.ArgumentParser(description="ETF Law Alert Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=15, help="Check interval in minutes (daemon mode)")
    parser.add_argument("--test", action="store_true", help="Send test alert")
    parser.add_argument("--force", action="store_true", help="Force alert even if already sent today")
    parser.add_argument("--discord", type=str, help="Discord webhook URL")
    parser.add_argument("--telegram", type=str, help="Telegram bot webhook URL")
    parser.add_argument("--slack", type=str, help="Slack webhook URL")

    args = parser.parse_args()

    # Setup channels
    channels = [ConsoleAlert(), FileAlert()]

    if args.discord:
        channels.append(WebhookAlert(args.discord, "discord"))
    if args.telegram:
        channels.append(WebhookAlert(args.telegram, "telegram"))
    if args.slack:
        channels.append(WebhookAlert(args.slack, "slack"))

    monitor = ETFLawMonitor(channels)

    if args.test:
        # Send test alert
        test_state = MarketState(
            timestamp=datetime.now().isoformat(),
            btc_price=95000,
            btc_ret_1d=-0.05,
            ibit_volume=50000000,
            ibit_vol_ratio=2.5,
            law_active=True,
            signal_strength="STRONG"
        )
        alert = monitor.create_alert(test_state)
        alert.title = "[TEST] " + alert.title
        monitor.send_alert(alert)
        print("Test alert sent!")

    elif args.daemon:
        monitor.run_daemon(args.interval)

    else:
        monitor.check_and_alert(force=args.force)


if __name__ == "__main__":
    main()
