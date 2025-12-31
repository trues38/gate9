"""
Unified Notification Service

Supports:
- Telegram Bot API
- Discord Webhooks
- Slack Webhooks (optional)

Usage:
    notifier = Notifier.from_env()
    notifier.send_alert(alert)
    notifier.send_decision_gate(decision)
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class NotifyPlatform(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"


@dataclass
class NotifyConfig:
    """Notification configuration"""
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'NotifyConfig':
        """Load config from environment variables"""
        return cls(
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
        )

    @classmethod
    def from_file(cls, path: str = None) -> 'NotifyConfig':
        """Load config from .env file"""
        env_path = path or str(Path(__file__).parent.parent.parent.parent / '.env')

        config = {}
        if Path(env_path).exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().strip('"\'')

        return cls(
            telegram_bot_token=config.get('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=config.get('TELEGRAM_CHAT_ID'),
            discord_webhook_url=config.get('DISCORD_WEBHOOK_URL'),
            slack_webhook_url=config.get('SLACK_WEBHOOK_URL'),
        )

    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def has_discord(self) -> bool:
        return bool(self.discord_webhook_url)

    def has_slack(self) -> bool:
        return bool(self.slack_webhook_url)


class TelegramNotifier:
    """Telegram Bot API integration"""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send text message"""
        url = self.BASE_URL.format(token=self.bot_token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    def send_alert(self, alert_type: str, title: str, message: str,
                   btc_price: float, btc_change: float,
                   ibit_vol_ratio: float, signal_strength: str) -> bool:
        """Send formatted alert"""
        emoji = {'ENTRY': '🟢', 'EXIT': '🔴', 'WARNING': '🟡'}.get(alert_type, '⚪')

        text = f"""
{emoji} *{title}*

{message}

📊 *Market State*
• BTC: ${btc_price:,.0f} ({btc_change*100:+.1f}%)
• IBIT Vol: {ibit_vol_ratio:.2f}x avg
• Signal: {signal_strength}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} KST
        """.strip()

        return self.send_message(text)

    def send_decision_gate(self, law_active: bool, checks: List[Dict],
                           verdict: str, action_text: str) -> bool:
        """Send decision gate status"""
        law_emoji = "🟢" if law_active else "⚪"
        verdict_emoji = {'DEPLOY': '🚀', 'HOLD': '⏸️', 'REJECT': '🚫'}.get(verdict, '❓')

        check_lines = []
        for c in checks:
            icon = "✅" if c['passed'] else "❌"
            check_lines.append(f"{icon} {c['name']}: {c['value']}")

        text = f"""
🎯 *DECISION GATE*

*Law Status:* {law_emoji} {'ACTIVE' if law_active else 'INACTIVE'}

*Checklist:*
{chr(10).join(check_lines)}

*Verdict:* {verdict_emoji} {verdict}
{action_text}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} KST
        """.strip()

        return self.send_message(text)


class DiscordNotifier:
    """Discord Webhook integration"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, content: str = None, embed: Dict = None) -> bool:
        """Send message to Discord"""
        payload = {}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Discord error: {e}")
            return False

    def send_alert(self, alert_type: str, title: str, message: str,
                   btc_price: float, btc_change: float,
                   ibit_vol_ratio: float, signal_strength: str) -> bool:
        """Send formatted alert"""
        color = {
            'ENTRY': 0x00FF00,   # Green
            'EXIT': 0xFF0000,    # Red
            'WARNING': 0xFFFF00  # Yellow
        }.get(alert_type, 0x808080)

        embed = {
            "title": f"🚨 {title}",
            "description": message,
            "color": color,
            "fields": [
                {"name": "BTC Price", "value": f"${btc_price:,.0f}", "inline": True},
                {"name": "BTC 1D", "value": f"{btc_change*100:+.1f}%", "inline": True},
                {"name": "IBIT Vol", "value": f"{ibit_vol_ratio:.2f}x", "inline": True},
                {"name": "Signal", "value": signal_strength, "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {"text": "BTC Macro Engine"}
        }

        return self.send_message(embed=embed)

    def send_decision_gate(self, law_active: bool, checks: List[Dict],
                           verdict: str, action_text: str) -> bool:
        """Send decision gate status"""
        color = {
            'DEPLOY': 0x00FF00,
            'HOLD': 0xFFFF00,
            'REJECT': 0xFF0000
        }.get(verdict, 0x808080)

        law_text = "🟢 ACTIVE" if law_active else "⚪ INACTIVE"
        verdict_emoji = {'DEPLOY': '🚀', 'HOLD': '⏸️', 'REJECT': '🚫'}.get(verdict, '❓')

        check_text = "\n".join([
            f"{'✅' if c['passed'] else '❌'} **{c['name']}**: {c['value']}"
            for c in checks
        ])

        embed = {
            "title": "🎯 DECISION GATE",
            "color": color,
            "fields": [
                {"name": "Law Status", "value": law_text, "inline": False},
                {"name": "Checklist", "value": check_text, "inline": False},
                {"name": f"Verdict: {verdict_emoji} {verdict}", "value": action_text, "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {"text": "BTC Macro Engine"}
        }

        return self.send_message(embed=embed)


class Notifier:
    """Unified notification manager"""

    def __init__(self, config: NotifyConfig):
        self.config = config
        self.telegram = None
        self.discord = None

        if config.has_telegram():
            self.telegram = TelegramNotifier(
                config.telegram_bot_token,
                config.telegram_chat_id
            )

        if config.has_discord():
            self.discord = DiscordNotifier(config.discord_webhook_url)

    @classmethod
    def from_env(cls) -> 'Notifier':
        """Create from environment variables"""
        return cls(NotifyConfig.from_env())

    @classmethod
    def from_file(cls, path: str = None) -> 'Notifier':
        """Create from .env file"""
        return cls(NotifyConfig.from_file(path))

    def get_active_platforms(self) -> List[str]:
        """Get list of configured platforms"""
        platforms = []
        if self.telegram:
            platforms.append("Telegram")
        if self.discord:
            platforms.append("Discord")
        return platforms

    def send_alert(self, alert_type: str, title: str, message: str,
                   btc_price: float, btc_change: float,
                   ibit_vol_ratio: float, signal_strength: str) -> Dict[str, bool]:
        """Send alert to all configured platforms"""
        results = {}

        if self.telegram:
            results['telegram'] = self.telegram.send_alert(
                alert_type, title, message,
                btc_price, btc_change, ibit_vol_ratio, signal_strength
            )

        if self.discord:
            results['discord'] = self.discord.send_alert(
                alert_type, title, message,
                btc_price, btc_change, ibit_vol_ratio, signal_strength
            )

        return results

    def send_decision_gate(self, law_active: bool, checks: List[Dict],
                           verdict: str, action_text: str) -> Dict[str, bool]:
        """Send decision gate to all configured platforms"""
        results = {}

        if self.telegram:
            results['telegram'] = self.telegram.send_decision_gate(
                law_active, checks, verdict, action_text
            )

        if self.discord:
            results['discord'] = self.discord.send_decision_gate(
                law_active, checks, verdict, action_text
            )

        return results

    def send_test(self) -> Dict[str, bool]:
        """Send test notification"""
        return self.send_alert(
            alert_type="WARNING",
            title="[TEST] BTC Macro Engine Connected",
            message="Test notification from BTC Macro Engine.\nAll systems operational.",
            btc_price=95000,
            btc_change=-0.02,
            ibit_vol_ratio=1.5,
            signal_strength="TEST"
        )


def test_notifications():
    """Test notification setup"""
    print("=" * 50)
    print("NOTIFICATION TEST")
    print("=" * 50)

    notifier = Notifier.from_file()

    platforms = notifier.get_active_platforms()
    if not platforms:
        print("\n❌ No platforms configured!")
        print("\nSetup instructions:")
        print("1. Copy .env.example to .env")
        print("2. Add your credentials:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        print("   DISCORD_WEBHOOK_URL=your_webhook_url")
        return

    print(f"\n✅ Active platforms: {', '.join(platforms)}")
    print("\nSending test notification...")

    results = notifier.send_test()

    for platform, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {platform}: {status}")


if __name__ == "__main__":
    test_notifications()
