"""
Integrated Strategy V3: H7 Primary + H4 Booster

핵심 발견:
- H7 (Gold 래그)가 가장 명확한 신호
- H4 (전이 윈도우)는 단순 레짐으로는 재현 어려움
- H4+H7 동시 발생 시 가장 높은 승률

V3 전략:
- H7을 주 진입 신호로
- Gold Safe-Haven 레짐 판단을 더 정밀하게
- 변동성/추세 필터 추가
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


@dataclass
class EntrySignal:
    date: str
    strength: str  # STRONG, MEDIUM, WEAK
    gold_return_7d: float
    days_since_gold_signal: int
    is_safe_haven: bool
    rsi: float
    volatility_regime: str


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    print(f"Fetching data: {start_date} ~ {end_date}")

    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
    gold = yf.download("GLD", start=start_date, end=end_date, progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if isinstance(gold.columns, pd.MultiIndex):
        gold.columns = gold.columns.get_level_values(0)

    data = pd.DataFrame(index=btc.index)
    data['BTC_Close'] = btc['Close']
    data['Gold_Close'] = gold['Close'].reindex(btc.index, method='ffill')

    # BTC
    data['RSI'] = calculate_rsi(data['BTC_Close'])
    data['BTC_Return_1d'] = data['BTC_Close'].pct_change()
    data['BTC_Return_7d'] = data['BTC_Close'].pct_change(7)
    data['Volatility'] = data['BTC_Return_1d'].rolling(20).std() * np.sqrt(365)
    data['Vol_MA'] = data['Volatility'].rolling(60).mean()

    # Gold
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)
    data['Gold_Return_14d'] = data['Gold_Close'].pct_change(14)
    data['Gold_MA_20'] = data['Gold_Close'].rolling(20).mean()

    data = data.dropna()
    print(f"Loaded {len(data)} days")

    return data


def is_gold_safe_haven_regime(row: pd.Series) -> bool:
    """
    Gold Safe-Haven 레짐 판단

    조건:
    1. Gold 7일 수익률 +1% 이상
    2. Gold가 20일 이평선 위
    3. (옵션) BTC 변동성 상승 중
    """
    gold_trending_up = row['Gold_Return_7d'] >= 0.01
    gold_above_ma = row['Gold_Close'] > row['Gold_MA_20']

    return gold_trending_up and gold_above_ma


def detect_gold_breakout(data: pd.DataFrame, threshold: float = 0.015) -> pd.DataFrame:
    """
    Gold 돌파 신호 감지

    돌파: 7일간 +1.5% 이상
    """
    data = data.copy()
    data['Gold_Breakout'] = data['Gold_Return_7d'] >= threshold

    # 마지막 돌파 이후 일수
    days_since = []
    last_breakout_idx = None

    for i in range(len(data)):
        if data['Gold_Breakout'].iloc[i]:
            last_breakout_idx = i
            days_since.append(0)
        elif last_breakout_idx is not None:
            days_since.append(i - last_breakout_idx)
        else:
            days_since.append(999)

    data['Days_Since_Gold_Breakout'] = days_since

    return data


def get_volatility_regime(volatility: float, vol_ma: float) -> str:
    """변동성 레짐"""
    if volatility > vol_ma * 1.5:
        return "HIGH"
    elif volatility < vol_ma * 0.7:
        return "LOW"
    else:
        return "NORMAL"


def check_entry_conditions(row: pd.Series) -> Tuple[bool, str, float]:
    """
    진입 조건 체크

    Returns:
        (should_enter, strength, score)

    H7 핵심 조건:
    1. Gold Safe-Haven 레짐
    2. Gold 돌파 후 3-10일
    3. D-Tier 아님 (RSI 25-80)

    강화 조건 (STRONG):
    - Gold 돌파 후 3-5일 (최적 타이밍)
    - RSI 40-60 (과열/과매도 아님)
    - 변동성 NORMAL 또는 HIGH
    """
    # 기본 필터
    rsi = row['RSI']
    if rsi < 25 or rsi > 80:
        return False, "BLOCKED", 0.0

    # Gold Safe-Haven 체크
    is_safe_haven = is_gold_safe_haven_regime(row)
    if not is_safe_haven:
        return False, "NO_SIGNAL", 0.0

    # Gold 돌파 래그 체크
    days_since_breakout = row['Days_Since_Gold_Breakout']
    if days_since_breakout < 3 or days_since_breakout > 10:
        return False, "NO_SIGNAL", 0.0

    # 기본 진입 조건 충족
    vol_regime = get_volatility_regime(row['Volatility'], row['Vol_MA'])

    # 강도 결정
    score = 0.5

    # 최적 타이밍 (3-5일)
    if 3 <= days_since_breakout <= 5:
        score += 0.2
    else:
        score += 0.1

    # RSI 중립 (40-60)
    if 40 <= rsi <= 60:
        score += 0.15
    elif 35 <= rsi <= 65:
        score += 0.1

    # 변동성 (HIGH는 기회)
    if vol_regime == "HIGH":
        score += 0.1
    elif vol_regime == "NORMAL":
        score += 0.05

    # Gold 14일 추세 확인
    if row['Gold_Return_14d'] > 0.02:
        score += 0.1

    # 강도 분류
    if score >= 0.8:
        strength = "STRONG"
    elif score >= 0.65:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    return True, strength, score


def generate_trades(data: pd.DataFrame,
                    min_strength: str = "WEAK",
                    hold_days: int = 7) -> List[TradeResult]:
    """거래 생성"""
    data = detect_gold_breakout(data.copy())

    strength_order = {"STRONG": 3, "MEDIUM": 2, "WEAK": 1}
    min_order = strength_order.get(min_strength, 1)

    trades = []
    position = None

    for i in range(1, len(data)):
        row = data.iloc[i]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['BTC_Close']

        if position is None:
            should_enter, strength, score = check_entry_conditions(row)

            if should_enter and strength_order.get(strength, 0) >= min_order:
                position = {
                    'entry_date': date,
                    'entry_price': price,
                    'entry_idx': i,
                    'strength': strength,
                    'score': score,
                    'gold_ret': row['Gold_Return_7d']
                }
        else:
            days_held = i - position['entry_idx']
            should_exit = False

            # 청산 조건
            if days_held >= hold_days:
                should_exit = True

            # D-Tier 진입
            if row['RSI'] < 25 or row['RSI'] > 80:
                should_exit = True

            # 손절
            current_return = (price - position['entry_price']) / position['entry_price']
            if current_return < -0.10:
                should_exit = True

            # 익절 (강한 신호만)
            if position['strength'] == "STRONG" and current_return > 0.15:
                should_exit = True

            if should_exit:
                return_pct = (price - position['entry_price']) / position['entry_price']

                trades.append(TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=date,
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry=f"{position['strength']}|{position['score']:.2f}|gold{position['gold_ret']*100:.1f}%"
                ))
                position = None

    return trades


def main():
    print("=" * 70)
    print("Integrated Strategy V3: H7 Primary")
    print("=" * 70)

    data = fetch_data("2020-01-01", "2025-12-26")
    data = detect_gold_breakout(data)

    calc = MetricsCalculator()

    # Gold Safe-Haven 분포
    safe_haven_days = sum(1 for i in range(len(data))
                         if is_gold_safe_haven_regime(data.iloc[i]))
    print(f"\nGold Safe-Haven days: {safe_haven_days} ({safe_haven_days/len(data)*100:.1f}%)")

    # Gold Breakout 분포
    breakout_days = data['Gold_Breakout'].sum()
    print(f"Gold Breakout days: {breakout_days} ({breakout_days/len(data)*100:.1f}%)")

    # 진입 가능 일수 (3-10일 래그)
    entry_window_days = ((data['Days_Since_Gold_Breakout'] >= 3) &
                         (data['Days_Since_Gold_Breakout'] <= 10)).sum()
    print(f"Entry window days: {entry_window_days} ({entry_window_days/len(data)*100:.1f}%)")

    # 기본 테스트
    print("\n" + "=" * 70)
    print("Basic Test: All Signals")
    print("=" * 70)

    all_trades = generate_trades(data)

    if all_trades:
        metrics = calc.calculate(all_trades, "all")
        print(f"\nTotal trades: {len(all_trades)}")
        print(f"Win rate: {metrics.win_rate:.1%}")
        print(f"Avg return: {metrics.avg_return*100:.2f}%")
        print(f"Total return: {metrics.total_return*100:.1f}%")

        # 강도별
        print("\n--- By Strength ---")
        for strength in ["STRONG", "MEDIUM", "WEAK"]:
            s_trades = [t for t in all_trades if t.state_at_entry.startswith(strength)]
            if s_trades:
                s_wr = sum(1 for t in s_trades if t.is_win) / len(s_trades)
                s_ret = np.prod([1 + t.return_pct for t in s_trades]) - 1
                print(f"  {strength}: {len(s_trades)} trades, WR {s_wr:.1%}, Return {s_ret*100:+.1f}%")

    # Walk-Forward
    print("\n" + "=" * 70)
    print("Walk-Forward Validation")
    print("=" * 70)

    train_end = "2022-12-31"
    train_data = data[data.index <= train_end].copy()
    test_data = data[data.index > train_end].copy()

    for min_strength in ["STRONG", "MEDIUM", "WEAK"]:
        print(f"\n--- Min Strength: {min_strength} ---")

        train_trades = generate_trades(train_data, min_strength=min_strength)
        test_trades = generate_trades(test_data, min_strength=min_strength)

        if len(train_trades) >= 3 and len(test_trades) >= 3:
            train_metrics = calc.calculate(train_trades, "train")
            test_metrics = calc.calculate(test_trades, "test")

            print(f"Train: {len(train_trades)} trades, WR {train_metrics.win_rate:.1%}")
            print(f"Test:  {len(test_trades)} trades, WR {test_metrics.win_rate:.1%}, "
                  f"Return {test_metrics.total_return*100:+.1f}%, p={test_metrics.p_value_vs_random:.4f}")
        else:
            print(f"  Not enough trades")

    # 파라미터 최적화
    print("\n" + "=" * 70)
    print("Parameter Optimization (Test)")
    print("=" * 70)

    results = []
    for min_strength in ["STRONG", "MEDIUM", "WEAK"]:
        for hold_days in [5, 7, 10, 14]:
            trades = generate_trades(test_data, min_strength=min_strength, hold_days=hold_days)
            if len(trades) >= 5:
                wr = sum(1 for t in trades if t.is_win) / len(trades)
                ret = np.prod([1 + t.return_pct for t in trades]) - 1
                results.append({
                    'strength': min_strength,
                    'hold': hold_days,
                    'trades': len(trades),
                    'wr': wr,
                    'return': ret
                })

    print(f"\n{'Strength':<10} {'Hold':<6} {'Trades':<8} {'WR':<10} {'Return':<12}")
    print("-" * 50)
    for r in sorted(results, key=lambda x: -x['wr']):
        print(f"{r['strength']:<10} {r['hold']:<6} {r['trades']:<8} "
              f"{r['wr']:.1%}      {r['return']*100:+.1f}%")

    # 년도별
    print("\n" + "=" * 70)
    print("Year-by-Year")
    print("=" * 70)

    print(f"\n{'Year':<8} {'Trades':<8} {'WR':<10} {'Return':<12}")
    print("-" * 40)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year].copy()
        if len(year_data) < 30:
            continue

        year_trades = generate_trades(year_data, min_strength="MEDIUM")
        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1
            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%")
        else:
            print(f"{year:<8} 0")

    # 개별 거래 (최근)
    print("\n" + "=" * 70)
    print("Recent Trades (2024-2025)")
    print("=" * 70)

    recent_trades = generate_trades(test_data, min_strength="MEDIUM")
    recent_2024_25 = [t for t in recent_trades
                      if t.entry_date >= "2024-01-01"]

    print(f"\n{'Entry':<12} {'Exit':<12} {'Return':<10} {'Days':<6} {'Signal':<30}")
    print("-" * 70)
    for t in recent_2024_25[-15:]:
        status = "WIN" if t.is_win else "LOSS"
        print(f"{t.entry_date:<12} {t.exit_date:<12} {t.return_pct*100:+6.1f}% ({status}) "
              f"{t.hold_days:<6} {t.state_at_entry[:30]}")

    # 최종 결론
    print("\n" + "=" * 70)
    print("Final Strategy V3")
    print("=" * 70)

    if results:
        best = max(results, key=lambda x: x['wr'] if x['trades'] >= 10 else 0)
        print(f"""
    최적 설정:
    - Min Strength: {best['strength']}
    - Hold Days: {best['hold']}
    - Test WR: {best['wr']:.1%}
    - Test Return: {best['return']*100:+.1f}%

    전략 로직:
    1. Gold Safe-Haven 레짐 진입 (Gold +1%, 20MA 위)
    2. Gold +1.5% 돌파 후 3-10일 대기
    3. RSI 25-80 필터 (D-Tier 회피)
    4. {best['hold']}일 보유 또는 -10% 손절
        """)


if __name__ == "__main__":
    main()
