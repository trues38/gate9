"""
BTC Trading Engine - Main Controller
통합 시그널 기반 자동매매 엔진
"""
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from btc_engine.core.config import EngineConfig, TradingConfig, APIConfig
from btc_engine.signals.calculator import SignalCalculator, MarketSnapshot
from btc_engine.storage.database import Database
from btc_engine.trading.executor import TradeExecutor
from btc_engine.trading.risk_manager import RiskManager, RiskLimits
from btc_engine.alerts.telegram import TelegramAlert, ConsoleAlert


class BTCEngine:
    """Main trading engine"""

    def __init__(self, config: EngineConfig = None):
        self.config = config or EngineConfig()
        self.config.validate()

        # Setup logging
        self._setup_logging()

        # Initialize components
        self.signal_calc = SignalCalculator(self.config.symbol)
        self.db = Database(self.config.db_path)
        self.executor = TradeExecutor(
            mode=self.config.trading.mode,
            api_key=self.config.api.binance_api_key,
            api_secret=self.config.api.binance_api_secret,
            initial_balance=self.config.trading.initial_capital
        )
        self.risk_manager = RiskManager(RiskLimits(
            max_position_pct=self.config.trading.max_position_pct,
            stop_loss_pct=self.config.trading.stop_loss_pct,
            take_profit_pct=self.config.trading.take_profit_pct,
            max_drawdown_pct=self.config.trading.max_drawdown_pct,
            max_daily_trades=self.config.trading.max_daily_trades,
            min_trade_interval_hours=self.config.trading.min_trade_interval_hours
        ))

        # Alerter
        if self.config.api.telegram_bot_token and self.config.api.telegram_chat_id:
            self.alerter = TelegramAlert(
                self.config.api.telegram_bot_token,
                self.config.api.telegram_chat_id
            )
        else:
            self.alerter = ConsoleAlert()

        # State
        self.running = False
        self.current_position = None
        self.entry_price = 0.0
        self.highest_since_entry = 0.0
        self.last_snapshot: Optional[MarketSnapshot] = None
        self.oco_order_id: Optional[str] = None

        # CRITICAL: Sync position on startup
        self._sync_position_on_startup()

        self.logger.info(f"Engine initialized | Mode: {self.config.trading.mode}")

    def _sync_position_on_startup(self):
        """CRITICAL: Sync position state with exchange on startup

        This prevents:
        - Double entries after restart
        - Orphaned positions without SL/TP
        - State mismatch between bot and exchange
        """
        self.logger.info("Syncing position state with exchange...")

        # 1. Check DB for open trades
        db_open_trades = self.db.get_open_trades()

        # 2. Check actual position from exchange
        actual_position = self.executor.get_position(self.config.symbol)

        if db_open_trades and actual_position.get("has_position"):
            # Both have position - resume tracking
            last_trade = db_open_trades[0]
            self.current_position = {
                'entry_price': last_trade['price'],
                'quantity': last_trade['quantity'],
                'entry_time': last_trade['timestamp'],
                'score': last_trade['score'],
                'verdict': last_trade['verdict'],
                'trade_id': last_trade['id']
            }
            self.entry_price = last_trade['price']
            self.highest_since_entry = last_trade['price']
            self.logger.info(f"Resumed position: {last_trade['quantity']:.6f} BTC @ ${last_trade['price']:,.0f}")

        elif db_open_trades and not actual_position.get("has_position"):
            # DB has position but exchange doesn't - position was closed externally
            self.logger.warning("DB has open trade but no exchange position - marking as closed")
            for trade in db_open_trades:
                # Get current price to estimate exit
                try:
                    current_price = self.signal_calc._get_json(
                        f"https://api.binance.com/api/v3/ticker/price?symbol={self.config.symbol}"
                    ).get("price", 0)
                    self.db.close_trade(trade['id'], float(current_price), "CLOSED", "EXTERNAL_CLOSE")
                except Exception:
                    self.db.close_trade(trade['id'], trade['price'], "UNKNOWN", "SYNC_CLOSE")

        elif not db_open_trades and actual_position.get("has_position"):
            # Exchange has position but DB doesn't - orphaned position
            self.logger.warning(f"Orphaned position found: {actual_position.get('btc_quantity'):.6f} BTC")
            self.alerter.send_error_alert(
                f"⚠️ Orphaned position detected: {actual_position.get('btc_quantity'):.6f} BTC\n"
                "Manual intervention may be required."
            )

        else:
            self.logger.info("No existing position - ready for new trades")

    def _setup_logging(self):
        """Setup logging"""
        log_path = Path(self.config.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('BTCEngine')

    def get_current_balance(self) -> float:
        """Get current USDT balance"""
        balance = self.executor.get_balance()
        if isinstance(balance, dict):
            return balance.get('usdt', balance.get('USDT', 0))
        return 0.0

    def check_and_execute_signals(self, snapshot: MarketSnapshot):
        """Check signals and execute trades if conditions met"""
        # CRITICAL: Check data reliability before any trading decision
        if not snapshot.is_reliable():
            self.logger.warning(
                f"Snapshot not reliable: {snapshot.valid_signals_count}/{snapshot.total_signals_count} valid, "
                f"candle_confirmed={snapshot.candle_confirmed}"
            )
            return

        balance = self.get_current_balance()
        self.risk_manager.update_peak_balance(balance)

        # Check if we can trade
        can_trade, reason = self.risk_manager.can_trade(
            balance, self.config.trading.initial_capital
        )

        if not can_trade:
            if "Kill switch" in reason:
                self.alerter.send_kill_switch_alert(reason, balance)
            self.logger.warning(f"Cannot trade: {reason}")
            return

        # Check existing position for exit
        if self.current_position:
            # Paper mode: Check if OCO would have triggered
            if self.executor.mode == "paper":
                oco_triggered = self.executor.check_oco_triggered(snapshot.price)
                if oco_triggered:
                    self._close_position(snapshot.price, oco_triggered)
                    return

            # Fallback local risk check (also acts as backup if OCO fails)
            should_exit, exit_type = self.risk_manager.should_exit(
                self.entry_price,
                snapshot.price,
                "BUY",
                self.highest_since_entry
            )

            if should_exit:
                self._close_position(snapshot.price, exit_type)
                return

            # Update highest price
            if snapshot.price > self.highest_since_entry:
                self.highest_since_entry = snapshot.price

        # Check for new entry
        if not self.current_position:
            if snapshot.total_score >= self.config.trading.buy_score_threshold:
                self._open_position(snapshot)

    def _open_position(self, snapshot: MarketSnapshot):
        """Open a new long position"""
        balance = self.get_current_balance()
        usdt_size, btc_size = self.risk_manager.calculate_position_size(
            balance, snapshot.price, snapshot.total_score
        )

        self.logger.info(f"Opening position: ${usdt_size:.2f} at ${snapshot.price:,.0f}")

        result = self.executor.buy(
            price=snapshot.price,
            usdt_amount=usdt_size,
            symbol=self.config.symbol
        )

        if result.success:
            self.current_position = {
                'entry_price': result.price,
                'quantity': result.quantity,
                'entry_time': result.timestamp,
                'score': snapshot.total_score,
                'verdict': snapshot.verdict
            }
            self.entry_price = result.price
            self.highest_since_entry = result.price

            # CRITICAL: Place OCO order for SL/TP on server
            oco_order_id = None
            oco_result = self.executor.create_oco_order(
                symbol=self.config.symbol,
                quantity=result.quantity,
                entry_price=result.price,
                stop_loss_pct=self.config.trading.stop_loss_pct,
                take_profit_pct=self.config.trading.take_profit_pct
            )

            if oco_result.success:
                oco_order_id = oco_result.order_list_id
                self.oco_order_id = oco_order_id
                self.logger.info(
                    f"OCO order placed: SL=${oco_result.stop_price:,.0f}, TP=${oco_result.limit_price:,.0f}"
                )
            else:
                self.logger.error(f"Failed to place OCO order: {oco_result.error}")
                self.alerter.send_error_alert(
                    f"⚠️ OCO order failed: {oco_result.error}\n"
                    "Position has no server-side SL/TP protection!"
                )

            # Record trade with action_taken
            self.risk_manager.record_trade()
            snapshot_id = self.db.save_snapshot(snapshot)
            trade_id = self.db.save_trade(
                "BUY", result.price, result.quantity,
                snapshot.total_score, snapshot.verdict, snapshot_id,
                action_taken="SIGNAL_BUY",
                oco_order_id=oco_order_id
            )
            self.current_position['trade_id'] = trade_id

            # Alert
            self.alerter.send_trade_alert(
                "BUY", result.price, result.quantity,
                snapshot.total_score, snapshot.verdict
            )

            self.logger.info(f"Position opened: {result.quantity:.6f} BTC @ ${result.price:,.2f}")
        else:
            self.logger.error(f"Failed to open position: {result.error}")
            self.alerter.send_error_alert(f"Failed to open position: {result.error}")

    def _close_position(self, price: float, exit_type: str):
        """Close current position"""
        if not self.current_position:
            return

        self.logger.info(f"Closing position: {exit_type} @ ${price:,.0f}")

        # CRITICAL: Cancel OCO order before selling (prevents double execution)
        if self.oco_order_id:
            try:
                self.executor.cancel_oco_order(self.config.symbol, self.oco_order_id)
                self.logger.info(f"OCO order cancelled: {self.oco_order_id}")
            except Exception as e:
                self.logger.warning(f"Failed to cancel OCO: {e}")

        result = self.executor.sell(
            price=price,
            btc_quantity=self.current_position['quantity'],
            symbol=self.config.symbol
        )

        if result.success:
            pnl = (result.price - self.entry_price) * result.quantity
            pnl_pct = (result.price - self.entry_price) / self.entry_price * 100

            # Map exit_type to action_taken
            action_map = {
                "STOP_LOSS": "SL_EXIT",
                "TAKE_PROFIT": "TP_EXIT",
                "TRAILING_STOP": "TRAILING_EXIT",
                "MANUAL": "MANUAL_EXIT"
            }
            action_taken = action_map.get(exit_type, exit_type)

            # Update database with action_taken
            if 'trade_id' in self.current_position:
                self.db.close_trade(
                    self.current_position['trade_id'],
                    result.price,
                    exit_type,
                    action_taken=action_taken
                )

            # Alert
            self.alerter.send_exit_alert(
                exit_type, self.entry_price, result.price, pnl, pnl_pct
            )

            self.logger.info(f"Position closed: ${pnl:,.2f} ({pnl_pct:+.2f}%) | Action: {action_taken}")

            # Reset
            self.current_position = None
            self.entry_price = 0.0
            self.highest_since_entry = 0.0
            self.oco_order_id = None
        else:
            self.logger.error(f"Failed to close position: {result.error}")
            self.alerter.send_error_alert(f"Failed to close position: {result.error}")

    def run_once(self) -> MarketSnapshot:
        """Run single iteration"""
        try:
            snapshot = self.signal_calc.create_snapshot()
            self.last_snapshot = snapshot

            # Save snapshot
            self.db.save_snapshot(snapshot)

            # Log
            self.logger.info(
                f"Snapshot: ${snapshot.price:,.0f} | "
                f"Score: {snapshot.total_score:+d} | "
                f"Verdict: {snapshot.verdict}"
            )

            # Check signals
            self.check_and_execute_signals(snapshot)

            return snapshot

        except Exception as e:
            self.logger.error(f"Error in run_once: {e}")
            self.alerter.send_error_alert(str(e))
            return None

    def run(self, interval_seconds: int = 60):
        """Run continuous loop"""
        self.running = True
        self.logger.info(f"Starting engine loop (interval: {interval_seconds}s)")

        while self.running:
            try:
                snapshot = self.run_once()

                # Send alert on significant signals
                if snapshot and snapshot.total_score >= self.config.trading.buy_score_threshold:
                    self.alerter.send_signal_alert(snapshot)

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop()
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(interval_seconds)

    def stop(self):
        """Stop the engine"""
        self.running = False
        self.logger.info("Engine stopped")

        # Send daily summary
        stats = self.db.get_trade_stats(days=1)
        balance = self.get_current_balance()
        self.alerter.send_daily_summary(stats, balance)

    def get_status(self) -> dict:
        """Get engine status"""
        balance = self.get_current_balance()
        risk_status = self.risk_manager.get_status(balance)
        trade_stats = self.db.get_trade_stats(days=30)

        return {
            "running": self.running,
            "mode": self.config.trading.mode,
            "balance": balance,
            "position": self.current_position,
            "last_snapshot": self.last_snapshot.to_dict() if self.last_snapshot else None,
            "risk": risk_status,
            "stats_30d": trade_stats
        }


def create_engine(mode: str = "paper", initial_capital: float = 1000.0) -> BTCEngine:
    """Factory function to create engine with common settings"""
    config = EngineConfig()
    config.trading.mode = mode
    config.trading.initial_capital = initial_capital

    return BTCEngine(config)
