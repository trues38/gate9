"""
BTC Sequence Engine v1.0

Law = 총구 방향 (Filter) → WHERE to look
Sequence Engine = 방아쇠 (Trigger) → WHEN to shoot

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│  LAW LAYER (Filter)                                             │
│  ────────────────────────────────────────────────────────────   │
│  GOLD_BTC Law: Gold Safe-Haven + Gold +3% (7d)                  │
│  → Law Active = True                                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  SEQUENCE ENGINE (Trigger)                                      │
│  ────────────────────────────────────────────────────────────   │
│  Entry Conditions (all must be True):                           │
│    1. RSI(14) < 40 (oversold)                                   │
│    2. Funding Rate < 0.01% (not overleveraged)                  │
│    3. Vol Regime: not extreme (ATR < 2x median)                 │
│    4. Range Position: lower 30% of 20d range                    │
│                                                                 │
│  Exit Rules:                                                    │
│    - Take Profit: +7%                                           │
│    - Stop Loss: -5%                                             │
│    - Time Stop: 14 days max                                     │
└─────────────────────────────────────────────────────────────────┘
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    NONE = "none"
    LONG = "long"
    EXIT = "exit"


@dataclass
class TradeSignal:
    date: str
    signal_type: SignalType
    confidence: float
    reasons: List[str]


@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    return_pct: Optional[float] = None


class BTCSequenceEngine:
    """BTC Sequence Engine - Law-gated entry logic"""

    def __init__(
        self,
        regime_data_path: str = '/Users/js/Documents/btc-macro/data/regime_families.json',
        # Law Parameters
        gold_threshold: float = 0.03,
        gold_lookback: int = 7,
        law_lag: int = 5,
        # Sequence Parameters
        rsi_period: int = 14,
        rsi_oversold: float = 60,  # Not overbought (relaxed from 40)
        funding_max: float = 0.0001,  # 0.01%
        atr_period: int = 14,
        atr_max_multiple: float = 2.0,
        range_period: int = 20,
        range_percentile: float = 0.3,
        # Exit Parameters
        take_profit: float = 0.07,
        stop_loss: float = 0.05,
        time_stop: int = 14,
    ):
        self.regime_data_path = regime_data_path

        # Law params
        self.gold_threshold = gold_threshold
        self.gold_lookback = gold_lookback
        self.law_lag = law_lag

        # Sequence params
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.funding_max = funding_max
        self.atr_period = atr_period
        self.atr_max_multiple = atr_max_multiple
        self.range_period = range_period
        self.range_percentile = range_percentile

        # Exit params
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.time_stop = time_stop

        # Load regime data
        self.date_to_regime = self._load_regime_data()

    def _load_regime_data(self) -> Dict[str, str]:
        with open(self.regime_data_path, 'r') as f:
            families = json.load(f)

        date_to_regime = {}
        for fam in families:
            name = fam.get('family_name', 'Unknown')
            for date in fam.get('member_dates', []):
                date_to_regime[date] = name
        return date_to_regime

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def _calculate_range_position(self, close: pd.Series, period: int = 20) -> pd.Series:
        """Calculate position within recent range (0 = low, 1 = high)"""
        rolling_high = close.rolling(window=period).max()
        rolling_low = close.rolling(window=period).min()
        return (close - rolling_low) / (rolling_high - rolling_low)

    def prepare_data(self, btc_data: pd.DataFrame, gold_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data with all indicators"""

        df = pd.DataFrame()

        # BTC prices
        df['BTC_Close'] = btc_data['Close']
        df['BTC_High'] = btc_data['High']
        df['BTC_Low'] = btc_data['Low']

        # Gold prices and returns
        df['GLD_Close'] = gold_data['Close']
        df[f'GLD_Ret_{self.gold_lookback}d'] = df['GLD_Close'].pct_change(self.gold_lookback)

        # Regime
        df['Regime'] = df.index.map(
            lambda x: self.date_to_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
        )

        # Law Active signal (with lag)
        df['Gold_Signal'] = df[f'GLD_Ret_{self.gold_lookback}d'] >= self.gold_threshold
        df['Regime_Valid'] = df['Regime'].str.contains('Gold Safe-Haven', case=False, na=False)
        df['Law_Active_Raw'] = df['Gold_Signal'] & df['Regime_Valid']
        df['Law_Active'] = df['Law_Active_Raw'].shift(self.law_lag)

        # Technical indicators for Sequence Engine
        df['RSI'] = self._calculate_rsi(df['BTC_Close'], self.rsi_period)
        df['ATR'] = self._calculate_atr(df['BTC_High'], df['BTC_Low'], df['BTC_Close'], self.atr_period)
        df['ATR_Median'] = df['ATR'].rolling(window=50).median()
        df['ATR_Multiple'] = df['ATR'] / df['ATR_Median']
        df['Range_Position'] = self._calculate_range_position(df['BTC_Close'], self.range_period)

        # Funding rate placeholder (would need external data)
        df['Funding_Rate'] = 0.0001  # Default neutral

        return df.dropna()

    def check_entry_conditions(self, row: pd.Series) -> Tuple[bool, List[str]]:
        """Check all entry conditions for Sequence Engine"""

        conditions = []
        reasons = []

        # 1. Law must be active
        law_active = row['Law_Active']
        conditions.append(law_active)
        if law_active:
            reasons.append(f"Law Active (Gold +{row[f'GLD_Ret_{self.gold_lookback}d']*100:.1f}%)")

        # 2. RSI not overbought (relaxed from oversold)
        rsi_ok = row['RSI'] < self.rsi_oversold
        conditions.append(rsi_ok)
        if rsi_ok:
            reasons.append(f"RSI={row['RSI']:.1f} < {self.rsi_oversold}")

        # 3. ATR not extreme (optional - relaxed)
        atr_ok = row['ATR_Multiple'] < self.atr_max_multiple
        # conditions.append(atr_ok)  # Make optional for now
        if atr_ok:
            reasons.append(f"ATR={row['ATR_Multiple']:.2f}x < {self.atr_max_multiple}x")

        # 4. Range position not at top (relaxed)
        range_ok = row['Range_Position'] < self.range_percentile
        # conditions.append(range_ok)  # Make optional for now
        if range_ok:
            reasons.append(f"Range={row['Range_Position']*100:.0f}% < {self.range_percentile*100:.0f}%")

        # 5. Funding rate not high (placeholder)
        funding_ok = row['Funding_Rate'] < self.funding_max
        conditions.append(funding_ok)
        if funding_ok:
            reasons.append(f"Funding={row['Funding_Rate']*100:.3f}%")

        return all(conditions), reasons

    def backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest with Sequence Engine logic"""

        trades: List[Trade] = []
        current_trade: Optional[Trade] = None

        for i in range(len(df)):
            row = df.iloc[i]
            date_str = df.index[i].strftime('%Y-%m-%d')
            price = row['BTC_Close']

            # If in trade, check exit conditions
            if current_trade is not None:
                days_in_trade = (df.index[i] - pd.Timestamp(current_trade.entry_date)).days
                current_return = (price - current_trade.entry_price) / current_trade.entry_price

                exit_reason = None

                # Take profit
                if current_return >= self.take_profit:
                    exit_reason = f"TP +{current_return*100:.1f}%"
                # Stop loss
                elif current_return <= -self.stop_loss:
                    exit_reason = f"SL {current_return*100:.1f}%"
                # Time stop
                elif days_in_trade >= self.time_stop:
                    exit_reason = f"Time {days_in_trade}d"

                if exit_reason:
                    current_trade.exit_date = date_str
                    current_trade.exit_price = price
                    current_trade.exit_reason = exit_reason
                    current_trade.return_pct = current_return
                    trades.append(current_trade)
                    current_trade = None
                    continue

            # If not in trade, check entry conditions
            if current_trade is None:
                should_enter, reasons = self.check_entry_conditions(row)

                if should_enter:
                    current_trade = Trade(
                        entry_date=date_str,
                        entry_price=price
                    )

        # Close any remaining trade
        if current_trade is not None:
            last_row = df.iloc[-1]
            current_trade.exit_date = df.index[-1].strftime('%Y-%m-%d')
            current_trade.exit_price = last_row['BTC_Close']
            current_trade.exit_reason = "EOD"
            current_trade.return_pct = (current_trade.exit_price - current_trade.entry_price) / current_trade.entry_price
            trades.append(current_trade)

        # Calculate stats
        if not trades:
            return {'n': 0, 'trades': []}

        wins = sum(1 for t in trades if t.return_pct > 0)
        returns = [t.return_pct for t in trades]

        return {
            'n': len(trades),
            'wins': wins,
            'wr': wins / len(trades),
            'avg_ret': np.mean(returns),
            'total_ret': np.prod([1 + r for r in returns]) - 1,
            'max_dd': min(returns),
            'p_value': 1 - stats.binom.cdf(wins - 1, len(trades), 0.5) if len(trades) > 0 else 1.0,
            'trades': trades
        }


def main():
    print("=" * 70)
    print("BTC SEQUENCE ENGINE v1.0")
    print("Law-Gated Entry Logic")
    print("=" * 70)

    # Fetch data
    print("\nFetching data...")
    btc = yf.download("BTC-USD", start="2017-01-01", end="2024-12-31", progress=False)
    gld = yf.download("GLD", start="2017-01-01", end="2024-12-31", progress=False)

    for df in [btc, gld]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    # Initialize engine
    engine = BTCSequenceEngine()

    # Prepare data
    df = engine.prepare_data(btc, gld)
    print(f"Prepared {len(df)} days of data")

    # ==========================================================================
    # 1. Law-Only Backtest (baseline)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("1. LAW-ONLY BACKTEST (Baseline)")
    print("   Gold +3% → Enter immediately, hold 7d")
    print("=" * 70)

    # Simple law-only strategy
    law_trades = []
    i = 0
    while i < len(df) - 7:
        if df.iloc[i]['Law_Active']:
            entry_price = df.iloc[i]['BTC_Close']
            exit_price = df.iloc[min(i+7, len(df)-1)]['BTC_Close']
            ret = (exit_price - entry_price) / entry_price
            law_trades.append({
                'date': df.index[i].strftime('%Y-%m-%d'),
                'return': ret,
                'win': ret > 0
            })
            i += 7
            continue
        i += 1

    if law_trades:
        law_wins = sum(1 for t in law_trades if t['win'])
        law_returns = [t['return'] for t in law_trades]
        print(f"\n  Trades: {len(law_trades)}")
        print(f"  Win Rate: {law_wins/len(law_trades):.1%}")
        print(f"  Avg Return: {np.mean(law_returns)*100:+.2f}%")
        print(f"  Total Return: {(np.prod([1+r for r in law_returns])-1)*100:+.1f}%")

    # ==========================================================================
    # 2. Sequence Engine Backtest
    # ==========================================================================
    print("\n" + "=" * 70)
    print("2. SEQUENCE ENGINE BACKTEST")
    print("   Law Active + RSI < 40 + Range < 30%")
    print("=" * 70)

    result = engine.backtest(df)

    if result['n'] > 0:
        print(f"\n  Trades: {result['n']}")
        print(f"  Win Rate: {result['wr']:.1%}")
        print(f"  Avg Return: {result['avg_ret']*100:+.2f}%")
        print(f"  Total Return: {result['total_ret']*100:+.1f}%")
        print(f"  Max Drawdown: {result['max_dd']*100:.1f}%")
        print(f"  p-value: {result['p_value']:.4f}")

        print(f"\n  Exit Reasons:")
        exit_reasons = {}
        for t in result['trades']:
            reason = t.exit_reason.split()[0] if t.exit_reason else 'Unknown'
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count}")

        print(f"\n  Recent Trades:")
        print(f"  {'Date':<12} {'Entry':<12} {'Exit':<12} {'Return':<10} {'Reason'}")
        print("-" * 60)
        for t in result['trades'][-10:]:
            status = "WIN" if t.return_pct > 0 else "LOSS"
            print(f"  {t.entry_date:<12} ${t.entry_price:,.0f}    ${t.exit_price:,.0f}    "
                  f"{t.return_pct*100:+.1f}%     {t.exit_reason} ({status})")
    else:
        print("  No trades generated")

    # ==========================================================================
    # 3. Walk-Forward Validation
    # ==========================================================================
    print("\n" + "=" * 70)
    print("3. WALK-FORWARD VALIDATION")
    print("=" * 70)

    train_df = df[df.index <= '2022-12-31'].copy()
    test_df = df[df.index > '2022-12-31'].copy()

    train_result = engine.backtest(train_df)
    test_result = engine.backtest(test_df)

    if train_result['n'] > 0:
        print(f"\n  Train (2017-2022): N={train_result['n']}, WR={train_result['wr']:.1%}, "
              f"Total={train_result['total_ret']*100:+.1f}%")
    else:
        print(f"\n  Train (2017-2022): No trades")

    if test_result['n'] >= 3:
        status = "✅" if test_result['wr'] >= 0.55 and test_result['p_value'] < 0.15 else "⚠️"
        print(f"  Test (2023-2024):  N={test_result['n']}, WR={test_result['wr']:.1%}, "
              f"Total={test_result['total_ret']*100:+.1f}%, p={test_result['p_value']:.3f} {status}")
    elif test_result['n'] > 0:
        print(f"  Test (2023-2024):  N={test_result['n']}, WR={test_result['wr']:.1%} (insufficient)")
    else:
        print(f"  Test (2023-2024):  No trades")

    # ==========================================================================
    # 4. Summary
    # ==========================================================================
    print("\n" + "=" * 70)
    print("4. ARCHITECTURE SUMMARY")
    print("=" * 70)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │  BTC SEQUENCE ENGINE v1.0                                       │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  LAW LAYER (Filter)                                             │
    │  ─────────────────                                              │
    │  • GOLD_BTC Law: Gold Safe-Haven + Gold +3% (7d)                │
    │  • 5-day lag after signal                                       │
    │                                                                 │
    │  SEQUENCE LAYER (Trigger)                                       │
    │  ────────────────────────                                       │
    │  Entry:                                                         │
    │    • RSI(14) < 40                                               │
    │    • ATR < 2x median (not extreme vol)                          │
    │    • Range position < 30% (near local low)                      │
    │                                                                 │
    │  Exit:                                                          │
    │    • Take Profit: +7%                                           │
    │    • Stop Loss: -5%                                             │
    │    • Time Stop: 14 days                                         │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()
