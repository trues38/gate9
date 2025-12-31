"""
BTC Trading Engine Configuration
"""
from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class TradingConfig:
    """Trading parameters"""
    # Mode
    mode: str = "paper"  # "paper" or "live"

    # Capital
    initial_capital: float = 1000.0  # USDT
    max_position_pct: float = 0.5    # Max 50% of capital per trade

    # Risk Management
    stop_loss_pct: float = 0.03      # 3% stop loss
    take_profit_pct: float = 0.05    # 5% take profit
    max_drawdown_pct: float = 0.15   # 15% max drawdown - kill switch
    max_daily_trades: int = 5

    # Signal Thresholds
    buy_score_threshold: int = 4
    strong_buy_threshold: int = 6
    sell_score_threshold: int = -3

    # Cooldown
    min_trade_interval_hours: int = 4


@dataclass
class APIConfig:
    """API credentials (from environment)"""
    binance_api_key: str = field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))


@dataclass
class EngineConfig:
    """Main engine configuration"""
    trading: TradingConfig = field(default_factory=TradingConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # Data
    symbol: str = "BTCUSDT"
    timeframes: list = field(default_factory=lambda: ["1m", "5m", "15m", "1h", "4h", "1d"])

    # Storage
    db_path: str = "data/btc_engine.db"
    log_path: str = "logs/btc_engine.log"

    # Update intervals (seconds)
    price_update_interval: int = 5
    signal_update_interval: int = 60

    def validate(self) -> bool:
        """Validate configuration"""
        if self.trading.mode == "live":
            if not self.api.binance_api_key or not self.api.binance_api_secret:
                raise ValueError("Binance API credentials required for live trading")
        return True
