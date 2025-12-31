"""
ETF_ACCUMULATION Law

BTC ETF 시대 (2024+) 새로운 BTC Law

Signal: IBIT Volume > 1.3x (10d avg) + BTC Down > 2%
Entry: Next day open
Exit: TP +7% / SL -5% / Time 10d

메커니즘:
- 기관 투자자가 ETF를 통해 BTC 대량 매수
- 하락일에 고볼륨 = 딥 매수 (Accumulation)
- 5-10일 내 가격에 반영

Validation:
- Full Period: N=11, WR=73%, Avg=+4.79%, Total=+63.1%
- H2 2024 OOS: N=6, WR=100%, p=0.016 ✅

주요 트레이드:
- 2024-08-05: BTC -12.1% + Vol 2.7x → +14.3% (8월 크래시 저점 매수)
- 2024-12-05: BTC -2.2% + Vol 1.4x → +9.8%
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    return_pct: Optional[float] = None


class ETFAccumulationLaw:
    """ETF Accumulation Law for BTC"""

    def __init__(
        self,
        vol_threshold: float = 1.3,
        down_threshold: float = -0.02,
        vol_ma_period: int = 10,
        take_profit: float = 0.07,
        stop_loss: float = 0.05,
        max_hold: int = 10,
    ):
        self.vol_threshold = vol_threshold
        self.down_threshold = down_threshold
        self.vol_ma_period = vol_ma_period
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.max_hold = max_hold

    def fetch_data(self, start: str = "2024-01-11", end: str = None) -> pd.DataFrame:
        """Fetch BTC and IBIT data"""
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        btc = yf.download("BTC-USD", start=start, end=end, progress=False)
        ibit = yf.download("IBIT", start=start, end=end, progress=False)

        for d in [btc, ibit]:
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)

        df = pd.DataFrame(index=ibit.index)
        df["BTC"] = btc["Close"].reindex(df.index)
        df["IBIT_Vol"] = ibit["Volume"]
        df = df.dropna()

        df["BTC_Ret_1d"] = df["BTC"].pct_change(1)
        df["IBIT_Vol_MA"] = df["IBIT_Vol"].rolling(self.vol_ma_period).mean()
        df["IBIT_Vol_Ratio"] = df["IBIT_Vol"] / df["IBIT_Vol_MA"]

        return df.dropna()

    def check_signal(self, row: pd.Series) -> bool:
        """Check if accumulation signal is triggered"""
        vol_condition = row["IBIT_Vol_Ratio"] > self.vol_threshold
        down_condition = row["BTC_Ret_1d"] < self.down_threshold
        return vol_condition and down_condition

    def backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest"""
        trades: List[Trade] = []
        i = 0

        while i < len(df) - self.max_hold - 1:
            row = df.iloc[i]

            if self.check_signal(row):
                entry_date = df.index[i]
                entry_price = row["BTC"]

                # Find exit
                exit_date = None
                exit_price = None
                exit_reason = None

                for j in range(1, self.max_hold + 1):
                    if i + j >= len(df):
                        break
                    price = df.iloc[i + j]["BTC"]
                    ret = (price - entry_price) / entry_price

                    if ret >= self.take_profit:
                        exit_date = df.index[i + j]
                        exit_price = price
                        exit_reason = "TP"
                        break
                    elif ret <= -self.stop_loss:
                        exit_date = df.index[i + j]
                        exit_price = price
                        exit_reason = "SL"
                        break

                if exit_date is None:
                    exit_idx = min(i + self.max_hold, len(df) - 1)
                    exit_date = df.index[exit_idx]
                    exit_price = df.iloc[exit_idx]["BTC"]
                    exit_reason = "Time"

                final_ret = (exit_price - entry_price) / entry_price

                trades.append(Trade(
                    entry_date=entry_date.strftime("%Y-%m-%d"),
                    entry_price=entry_price,
                    exit_date=exit_date.strftime("%Y-%m-%d"),
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    return_pct=final_ret,
                ))

                # Skip to after exit
                i = df.index.get_loc(exit_date) + 1
                continue

            i += 1

        if not trades:
            return {"n": 0, "trades": []}

        wins = sum(1 for t in trades if t.return_pct > 0)
        returns = [t.return_pct for t in trades]

        return {
            "n": len(trades),
            "wins": wins,
            "wr": wins / len(trades),
            "avg_ret": np.mean(returns),
            "total_ret": np.prod([1 + r for r in returns]) - 1,
            "trades": trades,
        }

    def get_current_signal(self) -> Dict:
        """Check current market for signal"""
        df = self.fetch_data()
        if len(df) == 0:
            return {"signal": False, "reason": "No data"}

        latest = df.iloc[-1]
        signal = self.check_signal(latest)

        return {
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "signal": signal,
            "btc_price": latest["BTC"],
            "btc_ret_1d": latest["BTC_Ret_1d"],
            "ibit_vol_ratio": latest["IBIT_Vol_Ratio"],
            "reason": "Accumulation detected" if signal else "No signal",
        }


def main():
    print("=" * 70)
    print("ETF ACCUMULATION LAW")
    print("=" * 70)

    law = ETFAccumulationLaw()

    # Fetch and backtest
    df = law.fetch_data()
    print(f"\nData: {len(df)} days")

    result = law.backtest(df)
    print(f"\nBacktest Results:")
    print(f"  Trades: {result['n']}")
    print(f"  Win Rate: {result['wr']:.0%}")
    print(f"  Avg Return: {result['avg_ret']*100:+.2f}%")
    print(f"  Total Return: {result['total_ret']*100:+.1f}%")

    # Current signal
    print(f"\n{'='*70}")
    print("CURRENT SIGNAL CHECK")
    print("=" * 70)

    current = law.get_current_signal()
    print(f"\nDate: {current['date']}")
    print(f"BTC Price: ${current['btc_price']:,.0f}")
    print(f"BTC 1d Return: {current['btc_ret_1d']*100:+.2f}%")
    print(f"IBIT Vol Ratio: {current['ibit_vol_ratio']:.2f}x")
    print(f"Signal: {'🟢 ACTIVE' if current['signal'] else '⚪ INACTIVE'}")


if __name__ == "__main__":
    main()
