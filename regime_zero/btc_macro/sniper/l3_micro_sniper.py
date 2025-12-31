"""
L3 Micro Sniper

Law가 방향을 정하면, 타점은 여기서 잡는다.

조건:
- ETF_ACCUMULATION Law ACTIVE일 때만 작동
- 1시간봉 RSI < 45 (눌림)
- VWAP 아래 → 재돌파 시 진입
- 실패 시 즉시 컷

Law = 총구 방향
Sniper = 방아쇠 타이밍
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')


@dataclass
class SniperSignal:
    timestamp: str
    law_active: bool
    rsi_1h: float
    price: float
    vwap: float
    price_vs_vwap: str  # 'above', 'below', 'breakout'
    entry_signal: bool
    reason: str


class L3MicroSniper:
    """L3 Micro Entry Sniper for BTC"""

    def __init__(
        self,
        rsi_threshold: float = 45,
        rsi_period: int = 14,
        vwap_period: int = 20,  # 20 hours for VWAP
        ibit_vol_threshold: float = 1.3,
        btc_down_threshold: float = -0.02,
    ):
        self.rsi_threshold = rsi_threshold
        self.rsi_period = rsi_period
        self.vwap_period = vwap_period
        self.ibit_vol_threshold = ibit_vol_threshold
        self.btc_down_threshold = btc_down_threshold

    def fetch_hourly_data(self, days: int = 7) -> pd.DataFrame:
        """Fetch hourly BTC data"""
        btc = yf.download(
            'BTC-USD',
            period=f'{days}d',
            interval='1h',
            progress=False
        )
        if isinstance(btc.columns, pd.MultiIndex):
            btc.columns = btc.columns.get_level_values(0)
        return btc

    def fetch_daily_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch daily BTC and IBIT data for Law check"""
        end = datetime.now()
        start = end - timedelta(days=30)

        btc = yf.download('BTC-USD', start=start, end=end, progress=False)
        ibit = yf.download('IBIT', start=start, end=end, progress=False)

        for df in [btc, ibit]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        return btc, ibit

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_vwap(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def check_law_active(self, btc_daily: pd.DataFrame, ibit_daily: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if ETF_ACCUMULATION Law is active
        Signal: IBIT Vol > 1.3x (10d avg) + BTC Down > 2%
        """
        if len(btc_daily) < 15 or len(ibit_daily) < 15:
            return False, "Insufficient data"

        # Align data
        common_idx = btc_daily.index.intersection(ibit_daily.index)
        btc = btc_daily.reindex(common_idx)
        ibit = ibit_daily.reindex(common_idx)

        # Calculate signals
        btc_ret_1d = btc['Close'].pct_change(1)
        ibit_vol_ma10 = ibit['Volume'].rolling(10).mean()
        ibit_vol_ratio = ibit['Volume'] / ibit_vol_ma10

        # Check last 3 days for active law (with lag consideration)
        for i in range(-3, 0):
            if i >= -len(btc_ret_1d) and i >= -len(ibit_vol_ratio):
                vol_ratio = ibit_vol_ratio.iloc[i]
                btc_down = btc_ret_1d.iloc[i]

                if vol_ratio > self.ibit_vol_threshold and btc_down < self.btc_down_threshold:
                    return True, f"Vol={vol_ratio:.1f}x, BTC={btc_down*100:.1f}%"

        return False, "No recent accumulation signal"

    def get_entry_signal(self) -> SniperSignal:
        """Get current entry signal"""
        # Fetch data
        hourly = self.fetch_hourly_data()
        btc_daily, ibit_daily = self.fetch_daily_data()

        if len(hourly) < self.rsi_period + 5:
            return SniperSignal(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
                law_active=False,
                rsi_1h=0,
                price=0,
                vwap=0,
                price_vs_vwap='unknown',
                entry_signal=False,
                reason="Insufficient hourly data"
            )

        # Check Law
        law_active, law_reason = self.check_law_active(btc_daily, ibit_daily)

        # Calculate hourly indicators
        hourly['RSI'] = self.calculate_rsi(hourly['Close'], self.rsi_period)
        hourly['VWAP'] = self.calculate_vwap(hourly, self.vwap_period)

        current = hourly.iloc[-1]
        prev = hourly.iloc[-2] if len(hourly) > 1 else current

        price = current['Close']
        rsi = current['RSI']
        vwap = current['VWAP']

        # Price vs VWAP
        if price > vwap:
            if prev['Close'] < prev['VWAP']:
                price_vs_vwap = 'breakout'  # Just broke above VWAP
            else:
                price_vs_vwap = 'above'
        else:
            price_vs_vwap = 'below'

        # Entry conditions
        conditions = []
        if law_active:
            conditions.append("Law ACTIVE")
        if rsi < self.rsi_threshold:
            conditions.append(f"RSI={rsi:.1f} < {self.rsi_threshold}")
        if price_vs_vwap == 'breakout':
            conditions.append("VWAP Breakout")

        # Full entry signal: Law + RSI + VWAP breakout
        entry_signal = (
            law_active and
            rsi < self.rsi_threshold and
            price_vs_vwap in ['breakout', 'above']
        )

        reason = " | ".join(conditions) if conditions else "No conditions met"

        return SniperSignal(
            timestamp=hourly.index[-1].strftime('%Y-%m-%d %H:%M'),
            law_active=law_active,
            rsi_1h=rsi,
            price=price,
            vwap=vwap,
            price_vs_vwap=price_vs_vwap,
            entry_signal=entry_signal,
            reason=reason
        )

    def print_status(self):
        """Print current sniper status"""
        signal = self.get_entry_signal()

        print("=" * 60)
        print("L3 MICRO SNIPER STATUS")
        print("=" * 60)
        print(f"\nTimestamp: {signal.timestamp}")
        print(f"BTC Price: ${signal.price:,.0f}")
        print()

        # Law Status
        law_icon = "🟢" if signal.law_active else "⚪"
        print(f"[LAW] ETF_ACCUMULATION: {law_icon} {'ACTIVE' if signal.law_active else 'INACTIVE'}")

        # RSI Status
        rsi_icon = "🟢" if signal.rsi_1h < self.rsi_threshold else "⚪"
        print(f"[RSI] 1H RSI: {signal.rsi_1h:.1f} {rsi_icon} (threshold: <{self.rsi_threshold})")

        # VWAP Status
        vwap_icon = "🟢" if signal.price_vs_vwap == 'breakout' else ("🟡" if signal.price_vs_vwap == 'above' else "⚪")
        print(f"[VWAP] Price vs VWAP: {signal.price_vs_vwap.upper()} {vwap_icon}")
        print(f"       VWAP: ${signal.vwap:,.0f}, Price: ${signal.price:,.0f}")

        print()
        print("-" * 60)

        # Final Signal
        if signal.entry_signal:
            print("🎯 ENTRY SIGNAL: ACTIVE")
            print(f"   Reason: {signal.reason}")
            print()
            print("   ACTION: LONG BTC")
            print("   STOP: 즉시 컷 if Law deactivates")
        else:
            print("⏸️  ENTRY SIGNAL: WAIT")
            print(f"   Missing: ", end="")
            missing = []
            if not signal.law_active:
                missing.append("Law inactive")
            if signal.rsi_1h >= self.rsi_threshold:
                missing.append(f"RSI too high ({signal.rsi_1h:.1f})")
            if signal.price_vs_vwap == 'below':
                missing.append("Below VWAP")
            print(", ".join(missing) if missing else "None")

        print()
        print("=" * 60)


def main():
    sniper = L3MicroSniper()
    sniper.print_status()


if __name__ == "__main__":
    main()
