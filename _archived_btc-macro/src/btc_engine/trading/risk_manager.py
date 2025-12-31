"""
Risk Management System
- Position sizing
- Stop loss / Take profit
- Max drawdown protection
- Daily trade limits
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List


@dataclass
class RiskLimits:
    """Risk management parameters"""
    max_position_pct: float = 0.5      # Max 50% of capital per trade
    stop_loss_pct: float = 0.03        # 3% stop loss
    take_profit_pct: float = 0.05      # 5% take profit
    trailing_stop_pct: float = 0.02    # 2% trailing stop after profit
    max_drawdown_pct: float = 0.15     # 15% max drawdown - kill switch
    max_daily_trades: int = 5
    min_trade_interval_hours: int = 4
    max_open_positions: int = 1


class RiskManager:
    """Risk management for trading"""

    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.daily_trades = []
        self.peak_balance = 0.0
        self.is_killed = False
        self.kill_reason = None

    def reset_daily(self):
        """Reset daily counters"""
        today = datetime.now().date()
        self.daily_trades = [t for t in self.daily_trades if t.date() == today]

    def can_trade(self, current_balance: float, initial_balance: float) -> tuple[bool, str]:
        """Check if trading is allowed"""
        # Kill switch active?
        if self.is_killed:
            return False, f"Kill switch active: {self.kill_reason}"

        # Check max drawdown
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
            if drawdown > self.limits.max_drawdown_pct:
                self.is_killed = True
                self.kill_reason = f"Max drawdown exceeded: {drawdown*100:.1f}%"
                return False, self.kill_reason

        # Check daily trade limit
        self.reset_daily()
        if len(self.daily_trades) >= self.limits.max_daily_trades:
            return False, f"Daily trade limit reached: {len(self.daily_trades)}/{self.limits.max_daily_trades}"

        # Check trade interval
        if self.daily_trades:
            last_trade = max(self.daily_trades)
            hours_since = (datetime.now() - last_trade).total_seconds() / 3600
            if hours_since < self.limits.min_trade_interval_hours:
                return False, f"Trade cooldown: wait {self.limits.min_trade_interval_hours - hours_since:.1f}h"

        return True, "OK"

    def calculate_position_size(self, balance: float, price: float, score: int) -> float:
        """Calculate position size based on score and risk limits"""
        # Base position: max_position_pct of balance
        base_size = balance * self.limits.max_position_pct

        # Adjust by signal strength
        if score >= 6:
            multiplier = 1.0  # Full position for strong signals
        elif score >= 4:
            multiplier = 0.75
        elif score >= 2:
            multiplier = 0.5
        else:
            multiplier = 0.25

        usdt_size = base_size * multiplier
        btc_size = usdt_size / price

        return usdt_size, btc_size

    def calculate_stop_loss(self, entry_price: float, side: str = "BUY") -> float:
        """Calculate stop loss price"""
        if side == "BUY":
            return entry_price * (1 - self.limits.stop_loss_pct)
        else:
            return entry_price * (1 + self.limits.stop_loss_pct)

    def calculate_take_profit(self, entry_price: float, side: str = "BUY") -> float:
        """Calculate take profit price"""
        if side == "BUY":
            return entry_price * (1 + self.limits.take_profit_pct)
        else:
            return entry_price * (1 - self.limits.take_profit_pct)

    def should_exit(self, entry_price: float, current_price: float, side: str = "BUY",
                    highest_since_entry: float = None) -> tuple[bool, str]:
        """Check if position should be exited"""

        if side == "BUY":
            pnl_pct = (current_price - entry_price) / entry_price

            # Stop loss
            if pnl_pct <= -self.limits.stop_loss_pct:
                return True, "STOP_LOSS"

            # Take profit
            if pnl_pct >= self.limits.take_profit_pct:
                return True, "TAKE_PROFIT"

            # Trailing stop (if in profit)
            if highest_since_entry and pnl_pct > 0:
                drop_from_high = (highest_since_entry - current_price) / highest_since_entry
                if drop_from_high >= self.limits.trailing_stop_pct:
                    return True, "TRAILING_STOP"

        else:  # SHORT
            pnl_pct = (entry_price - current_price) / entry_price

            if pnl_pct <= -self.limits.stop_loss_pct:
                return True, "STOP_LOSS"

            if pnl_pct >= self.limits.take_profit_pct:
                return True, "TAKE_PROFIT"

        return False, None

    def record_trade(self):
        """Record a trade for daily tracking"""
        self.daily_trades.append(datetime.now())

    def update_peak_balance(self, balance: float):
        """Update peak balance for drawdown calculation"""
        if balance > self.peak_balance:
            self.peak_balance = balance

    def get_status(self, current_balance: float) -> dict:
        """Get risk management status"""
        drawdown = 0.0
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance

        self.reset_daily()

        return {
            "is_killed": self.is_killed,
            "kill_reason": self.kill_reason,
            "peak_balance": self.peak_balance,
            "current_drawdown": drawdown,
            "max_drawdown": self.limits.max_drawdown_pct,
            "daily_trades": len(self.daily_trades),
            "max_daily_trades": self.limits.max_daily_trades
        }
