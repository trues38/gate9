"""
Signal Calculator - 검증된 지표 기반 스코어링
"""
import urllib.request
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import math


@dataclass
class Signal:
    """Individual signal"""
    name: str
    value: float
    score: int
    description: str
    is_valid: bool = True  # False if data was missing


@dataclass
class MarketSnapshot:
    """Complete market state snapshot"""
    timestamp: datetime
    price: float
    rsi: float
    bb_position: float
    fng: Optional[int]  # None if API failed
    funding_rate: Optional[float]
    ls_ratio: Optional[float]
    top_ls_ratio: Optional[float]
    consecutive_down: int
    consecutive_up: int
    signals: List[Signal]
    total_score: int
    verdict: str
    valid_signals_count: int = 0  # How many signals had valid data
    total_signals_count: int = 0  # Total signals attempted
    candle_confirmed: bool = True  # False if using unconfirmed candle

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "rsi": self.rsi,
            "bb_position": self.bb_position,
            "fng": self.fng,
            "funding_rate": self.funding_rate,
            "ls_ratio": self.ls_ratio,
            "top_ls_ratio": self.top_ls_ratio,
            "consecutive_down": self.consecutive_down,
            "consecutive_up": self.consecutive_up,
            "total_score": self.total_score,
            "verdict": self.verdict,
            "valid_signals_count": self.valid_signals_count,
            "total_signals_count": self.total_signals_count,
            "candle_confirmed": self.candle_confirmed,
            "signals": [{"name": s.name, "value": s.value, "score": s.score, "valid": s.is_valid} for s in self.signals]
        }

    def is_reliable(self) -> bool:
        """Check if snapshot has enough valid data for trading"""
        # Require at least 70% valid signals and confirmed candle
        if self.total_signals_count == 0:
            return False
        validity_ratio = self.valid_signals_count / self.total_signals_count
        return validity_ratio >= 0.7 and self.candle_confirmed


class SignalCalculator:
    """Calculate trading signals from market data"""

    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol

    def _get_json(self, url: str, timeout: int = 10) -> dict:
        """Fetch JSON from URL"""
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())

    def _calc_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50.0

        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period if sum(losses[-period:]) > 0 else 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calc_bb_position(self, closes: List[float], period: int = 20) -> float:
        """Calculate Bollinger Band position (0-100)"""
        if len(closes) < period:
            return 50.0

        window = closes[-period:]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)

        if std == 0:
            return 50.0

        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std
        current = closes[-1]

        return max(0, min(100, (current - bb_lower) / (bb_upper - bb_lower) * 100))

    def _count_consecutive(self, candles: list, direction: str) -> int:
        """Count consecutive up or down days"""
        count = 0
        for i in range(len(candles) - 1, 0, -1):
            close = float(candles[i][4])
            open_ = float(candles[i][1])

            if direction == "down" and close < open_:
                count += 1
            elif direction == "up" and close > open_:
                count += 1
            else:
                break
        return count

    def fetch_market_data(self) -> dict:
        """Fetch all required market data"""
        data = {}
        data["_errors"] = []  # Track which APIs failed

        # Price & Candles
        candles = self._get_json(
            f"https://api.binance.com/api/v3/klines?symbol={self.symbol}&interval=1d&limit=100"
        )
        data["candles"] = candles

        # CRITICAL: Check if last candle is closed
        # Binance kline format: [open_time, open, high, low, close, volume, close_time, ...]
        last_candle = candles[-1]
        last_close_time = last_candle[6]  # close_time in ms
        current_time = datetime.now().timestamp() * 1000

        if current_time < last_close_time:
            # Last candle is NOT closed yet - exclude it for indicator calculation
            data["closes"] = [float(c[4]) for c in candles[:-1]]
            data["candle_confirmed"] = False
        else:
            # Last candle is closed
            data["closes"] = [float(c[4]) for c in candles]
            data["candle_confirmed"] = True

        # Current price (always use latest, even if candle not closed)
        data["price"] = float(candles[-1][4])

        # Fear & Greed - None if failed
        try:
            fng_data = self._get_json("https://api.alternative.me/fng/?limit=1")
            data["fng"] = int(fng_data["data"][0]["value"])
        except Exception as e:
            data["fng"] = None
            data["_errors"].append(f"FNG: {e}")

        # Funding Rate - None if failed
        try:
            funding = self._get_json(
                f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={self.symbol}&limit=1"
            )
            data["funding_rate"] = float(funding[0]["fundingRate"]) * 100
        except Exception as e:
            data["funding_rate"] = None
            data["_errors"].append(f"Funding: {e}")

        # Long/Short Ratio - None if failed
        try:
            ls = self._get_json(
                f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={self.symbol}&period=1d&limit=1"
            )
            data["ls_ratio"] = float(ls[0]["longShortRatio"])
        except Exception as e:
            data["ls_ratio"] = None
            data["_errors"].append(f"L/S: {e}")

        # Top Traders L/S - None if failed
        try:
            top_ls = self._get_json(
                f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={self.symbol}&period=1d&limit=1"
            )
            data["top_ls_ratio"] = float(top_ls[0]["longShortRatio"])
        except Exception as e:
            data["top_ls_ratio"] = None
            data["_errors"].append(f"TopLS: {e}")

        return data

    def calculate_signals(self, data: dict) -> List[Signal]:
        """Calculate individual signals from market data

        CRITICAL: Signals with None data are marked is_valid=False
        and scored as 0 (excluded from total score)
        """
        signals = []

        # RSI (always valid - uses local price data)
        rsi = self._calc_rsi(data["closes"])
        if rsi < 25:
            signals.append(Signal("RSI", rsi, 3, "극과매도", is_valid=True))
        elif rsi < 30:
            signals.append(Signal("RSI", rsi, 2, "과매도", is_valid=True))
        elif rsi < 40:
            signals.append(Signal("RSI", rsi, 1, "약세", is_valid=True))
        elif rsi > 70:
            signals.append(Signal("RSI", rsi, -2, "과매수", is_valid=True))
        else:
            signals.append(Signal("RSI", rsi, 0, "중립", is_valid=True))

        # Bollinger Bands (always valid - uses local price data)
        bb_pos = self._calc_bb_position(data["closes"])
        if bb_pos < 5:
            signals.append(Signal("BB", bb_pos, 2, "하단터치", is_valid=True))
        elif bb_pos < 20:
            signals.append(Signal("BB", bb_pos, 1, "하단근접", is_valid=True))
        elif bb_pos > 95:
            signals.append(Signal("BB", bb_pos, -2, "상단터치", is_valid=True))
        else:
            signals.append(Signal("BB", bb_pos, 0, "중립", is_valid=True))

        # Fear & Greed - SKIP if None
        fng = data.get("fng")
        if fng is not None:
            if fng <= 20:
                signals.append(Signal("FNG", fng, 2, "Extreme Fear", is_valid=True))
            elif fng <= 30:
                signals.append(Signal("FNG", fng, 1, "Fear", is_valid=True))
            elif fng >= 80:
                signals.append(Signal("FNG", fng, -2, "Extreme Greed", is_valid=True))
            else:
                signals.append(Signal("FNG", fng, 0, "중립", is_valid=True))
        else:
            signals.append(Signal("FNG", 0, 0, "데이터없음", is_valid=False))

        # Funding Rate - SKIP if None
        funding = data.get("funding_rate")
        if funding is not None:
            if funding < -0.01:
                signals.append(Signal("Funding", funding, 2, "강한 음수", is_valid=True))
            elif funding < 0:
                signals.append(Signal("Funding", funding, 1, "음수", is_valid=True))
            elif funding > 0.05:
                signals.append(Signal("Funding", funding, -1, "높음", is_valid=True))
            else:
                signals.append(Signal("Funding", funding, 0, "중립", is_valid=True))
        else:
            signals.append(Signal("Funding", 0, 0, "데이터없음", is_valid=False))

        # L/S Ratio - SKIP if None
        ls = data.get("ls_ratio")
        if ls is not None:
            if ls > 2.5:
                signals.append(Signal("L/S", ls, -1, "롱과다", is_valid=True))
            elif ls < 1.0:
                signals.append(Signal("L/S", ls, 1, "숏과다", is_valid=True))
            else:
                signals.append(Signal("L/S", ls, 0, "중립", is_valid=True))
        else:
            signals.append(Signal("L/S", 0, 0, "데이터없음", is_valid=False))

        # Top Traders - SKIP if None
        top_ls = data.get("top_ls_ratio")
        if top_ls is not None:
            if top_ls > 2.0:
                signals.append(Signal("TopTraders", top_ls, 1, "고래롱", is_valid=True))
            elif top_ls < 0.8:
                signals.append(Signal("TopTraders", top_ls, -1, "고래숏", is_valid=True))
            else:
                signals.append(Signal("TopTraders", top_ls, 0, "중립", is_valid=True))
        else:
            signals.append(Signal("TopTraders", 0, 0, "데이터없음", is_valid=False))

        # Consecutive days (always valid - uses local candle data)
        down_days = self._count_consecutive(data["candles"], "down")
        if down_days >= 4:
            signals.append(Signal("ConsecDown", down_days, 2, f"{down_days}일연속하락", is_valid=True))
        elif down_days >= 3:
            signals.append(Signal("ConsecDown", down_days, 1, f"{down_days}일연속하락", is_valid=True))

        up_days = self._count_consecutive(data["candles"], "up")
        if up_days >= 4:
            signals.append(Signal("ConsecUp", up_days, -1, f"{up_days}일연속상승", is_valid=True))

        return signals

    def get_verdict(self, score: int) -> str:
        """Get trading verdict from score"""
        if score >= 6:
            return "STRONG_BUY"
        elif score >= 4:
            return "BUY"
        elif score >= 2:
            return "LEAN_LONG"
        elif score <= -4:
            return "SELL"
        elif score <= -2:
            return "LEAN_SHORT"
        else:
            return "NEUTRAL"

    def create_snapshot(self) -> MarketSnapshot:
        """Create complete market snapshot"""
        data = self.fetch_market_data()
        signals = self.calculate_signals(data)

        # CRITICAL: Only count valid signals for total score
        valid_signals = [s for s in signals if s.is_valid]
        total_score = sum(s.score for s in valid_signals)

        return MarketSnapshot(
            timestamp=datetime.now(),
            price=data["price"],
            rsi=self._calc_rsi(data["closes"]),
            bb_position=self._calc_bb_position(data["closes"]),
            fng=data.get("fng"),  # Can be None
            funding_rate=data.get("funding_rate"),
            ls_ratio=data.get("ls_ratio"),
            top_ls_ratio=data.get("top_ls_ratio"),
            consecutive_down=self._count_consecutive(data["candles"], "down"),
            consecutive_up=self._count_consecutive(data["candles"], "up"),
            signals=signals,
            total_score=total_score,
            verdict=self.get_verdict(total_score),
            valid_signals_count=len(valid_signals),
            total_signals_count=len(signals),
            candle_confirmed=data.get("candle_confirmed", True)
        )
