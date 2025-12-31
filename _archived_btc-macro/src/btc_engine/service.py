"""
BTC Macro Engine - SaaS Service

Main service that runs on VPS:
- Hourly Law signal check (after US market close)
- Daily META health report
- Real-time notifications via Telegram/Discord

Usage:
    python service.py              # Run once
    python service.py --daemon     # Daemon mode
    python service.py --test       # Test notifications
"""

import os
import sys
import time
import signal
import argparse
import schedule
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from btc_engine.alerts.notifier import Notifier
from btc_engine.alerts.etf_law_monitor import ETFLawMonitor, ConsoleAlert, FileAlert
from btc_engine.meta.law_health_monitor import LawHealthMonitor, RegimeDriftDetector
from btc_engine.meta.decision_gate import HumanDecisionGate


class BTCMacroService:
    """Main service class"""

    def __init__(self):
        self.notifier = Notifier.from_file()
        self.law_monitor = ETFLawMonitor(channels=[ConsoleAlert(), FileAlert()])
        self.health_monitor = LawHealthMonitor()
        self.drift_detector = RegimeDriftDetector()
        self.decision_gate = HumanDecisionGate()

        self.running = False
        self.last_signal_date = None

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        print("\n[Service] Shutting down...")
        self.running = False

    def _log(self, message: str):
        """Log with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")

    def check_law_and_notify(self):
        """Check law signal and send notification if active"""
        self._log("Checking ETF Accumulation Law...")

        state = self.law_monitor.fetch_market_data()
        if state is None:
            self._log("Failed to fetch market data")
            return

        today = datetime.now().strftime('%Y-%m-%d')

        # Log status
        self._log(f"BTC: ${state.btc_price:,.0f} ({state.btc_ret_1d*100:+.1f}%)")
        self._log(f"IBIT Vol: {state.ibit_vol_ratio:.2f}x")
        self._log(f"Law Active: {state.law_active}")

        # Only notify if law is active and not already notified today
        if state.law_active and self.last_signal_date != today:
            self._log("LAW SIGNAL DETECTED! Sending notifications...")

            # Get decision gate status
            decision = self.decision_gate.evaluate(law_active=True)

            # Send alert
            alert_results = self.notifier.send_alert(
                alert_type="ENTRY",
                title="ETF ACCUMULATION SIGNAL DETECTED",
                message=f"기관 ETF 딥 매수 감지!\n• IBIT 볼륨: {state.ibit_vol_ratio:.1f}x\n• BTC 하락: {state.btc_ret_1d*100:.1f}%",
                btc_price=state.btc_price,
                btc_change=state.btc_ret_1d,
                ibit_vol_ratio=state.ibit_vol_ratio,
                signal_strength=state.signal_strength
            )

            # Send decision gate
            checks = [
                {'name': 'META Health', 'value': f"{decision.checks[0].value}", 'passed': decision.checks[0].passed},
                {'name': 'Regime Drift', 'value': decision.checks[1].value, 'passed': decision.checks[1].passed},
                {'name': 'Vol Asymmetry', 'value': decision.checks[2].value, 'passed': decision.checks[2].passed},
                {'name': 'ETF Structure', 'value': decision.checks[3].value, 'passed': decision.checks[3].passed},
            ]

            gate_results = self.notifier.send_decision_gate(
                law_active=True,
                checks=checks,
                verdict=decision.verdict,
                action_text=decision.action_text
            )

            self.last_signal_date = today

            for platform, success in alert_results.items():
                status = "sent" if success else "failed"
                self._log(f"  {platform}: {status}")

        else:
            self._log("No signal")

    def send_daily_report(self):
        """Send daily health report"""
        self._log("Generating daily report...")

        health = self.health_monitor.calculate_health()
        drift = self.drift_detector.detect_drift()
        decision = self.decision_gate.evaluate(law_active=False)

        checks = [
            {'name': 'META Health', 'value': f"{decision.checks[0].value}", 'passed': decision.checks[0].passed},
            {'name': 'Regime Drift', 'value': decision.checks[1].value, 'passed': decision.checks[1].passed},
            {'name': 'Vol Asymmetry', 'value': decision.checks[2].value, 'passed': decision.checks[2].passed},
            {'name': 'ETF Structure', 'value': decision.checks[3].value, 'passed': decision.checks[3].passed},
        ]

        results = self.notifier.send_decision_gate(
            law_active=False,
            checks=checks,
            verdict=decision.verdict,
            action_text=f"Daily Report - Health: {health.health_score}/100, Status: {health.health_status}"
        )

        for platform, success in results.items():
            status = "sent" if success else "failed"
            self._log(f"  Daily report {platform}: {status}")

    def test_notifications(self):
        """Send test notification"""
        self._log("Sending test notification...")

        platforms = self.notifier.get_active_platforms()
        if not platforms:
            self._log("No platforms configured! Check .env file.")
            return False

        self._log(f"Active platforms: {', '.join(platforms)}")

        results = self.notifier.send_test()

        success = True
        for platform, result in results.items():
            status = "OK" if result else "FAILED"
            self._log(f"  {platform}: {status}")
            if not result:
                success = False

        return success

    def run_once(self):
        """Run single check"""
        self.check_law_and_notify()

    def run_daemon(self, check_interval: int = 60):
        """Run as daemon with scheduled checks"""
        self._log(f"Starting daemon mode (interval: {check_interval} min)")
        self._log(f"Active platforms: {', '.join(self.notifier.get_active_platforms())}")

        self.running = True

        # Schedule jobs
        # Check law every hour at :05 (after potential data updates)
        schedule.every().hour.at(":05").do(self.check_law_and_notify)

        # Daily report at 09:00 KST
        schedule.every().day.at("09:00").do(self.send_daily_report)

        # Also check immediately on start
        self.check_law_and_notify()

        self._log("Daemon started. Press Ctrl+C to stop.")

        while self.running:
            schedule.run_pending()
            time.sleep(60)

        self._log("Daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="BTC Macro Engine Service")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--test", action="store_true", help="Test notifications")
    parser.add_argument("--interval", type=int, default=60, help="Check interval (minutes)")
    parser.add_argument("--daily-report", action="store_true", help="Send daily report now")

    args = parser.parse_args()

    service = BTCMacroService()

    if args.test:
        service.test_notifications()
    elif args.daily_report:
        service.send_daily_report()
    elif args.daemon:
        service.run_daemon(args.interval)
    else:
        service.run_once()


if __name__ == "__main__":
    main()
