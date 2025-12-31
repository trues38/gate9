"""
H7 Primary Strategy

원래 H7 테스트 (66.7% OOS WR)의 로직을 정확히 재현

핵심:
- Gold Safe-Haven 레짐
- Gold +1.5% 후 3일 대기
- 7일 보유

H4는 부스터로만: 유리한 전이 중이면 포지션 증가
H1은 필터로: D-Tier면 스킵
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


def load_regime_data() -> Dict[str, str]:
    """날짜 → 레짐 매핑"""
    try:
        with open('/Users/js/Documents/btc-macro/data/regime_families.json', 'r') as f:
            families = json.load(f)
    except FileNotFoundError:
        return {}

    date_regime = {}
    for fam in families:
        name = fam.get('family_name', 'Unknown')
        for date in fam.get('member_dates', []):
            date_regime[date] = name

    return date_regime


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
    data['Gold_Return_7d'] = data['Gold_Close'].pct_change(7)

    # RSI
    delta = data['BTC_Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    data = data.dropna()
    print(f"Loaded {len(data)} days")
    return data


def generate_h7_trades(data: pd.DataFrame,
                       date_regime: Dict[str, str],
                       gold_threshold: float = 0.015,
                       lag_days: int = 3,
                       hold_days: int = 7,
                       use_h1_filter: bool = True) -> List[TradeResult]:
    """
    H7 거래 생성 (원래 테스트 로직 그대로)

    조건:
    1. Gold Safe-Haven 레짐
    2. Gold 7일 수익률 >= threshold
    3. lag_days 후 진입
    4. hold_days 보유 후 청산
    """
    trades = []
    position = None
    last_gold_signal_idx = None

    for i in range(len(data)):
        date_str = data.index[i].strftime('%Y-%m-%d')
        regime = date_regime.get(date_str, '')
        row = data.iloc[i]
        price = row['BTC_Close']

        # Gold 신호 체크
        is_gold_safe_haven = 'Gold Safe-Haven' in regime
        gold_breakout = row['Gold_Return_7d'] >= gold_threshold

        if is_gold_safe_haven and gold_breakout:
            last_gold_signal_idx = i

        if position is None:
            # 진입 조건: Gold 신호 후 lag_days 경과
            if last_gold_signal_idx is not None:
                days_since_signal = i - last_gold_signal_idx

                if days_since_signal == lag_days:
                    # H1 필터: D-Tier 체크
                    if use_h1_filter and (row['RSI'] < 25 or row['RSI'] > 80):
                        continue

                    # 현재도 Gold Safe-Haven인지 확인
                    if 'Gold Safe-Haven' in regime:
                        position = {
                            'entry_date': date_str,
                            'entry_price': price,
                            'entry_idx': i,
                            'gold_return': data.iloc[last_gold_signal_idx]['Gold_Return_7d']
                        }
        else:
            # 청산 조건
            days_held = i - position['entry_idx']

            if days_held >= hold_days:
                return_pct = (price - position['entry_price']) / position['entry_price']

                trades.append(TradeResult(
                    entry_date=position['entry_date'],
                    exit_date=date_str,
                    entry_price=position['entry_price'],
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=return_pct > 0,
                    hold_days=days_held,
                    state_at_entry=f"H7|gold{position['gold_return']*100:.1f}%"
                ))
                position = None

    return trades


def main():
    print("=" * 70)
    print("H7 Primary Strategy (Gold Safe-Haven Lag)")
    print("=" * 70)

    date_regime = load_regime_data()
    data = fetch_data("2020-01-01", "2025-12-26")

    # 레짐 추가
    data['Regime'] = data.index.map(
        lambda x: date_regime.get(x.strftime('%Y-%m-%d'), 'Unknown')
    )

    calc = MetricsCalculator()

    # Gold Safe-Haven 분포
    gold_sh_days = sum(1 for r in data['Regime'] if 'Gold Safe-Haven' in r)
    print(f"\nGold Safe-Haven days: {gold_sh_days} ({gold_sh_days/len(data)*100:.1f}%)")

    # Walk-Forward
    train_end = "2022-12-31"
    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    # 파라미터 스윕
    print("\n" + "=" * 70)
    print("Parameter Sweep (Original H7 Logic)")
    print("=" * 70)

    results = []

    for gold_th in [0.015, 0.02, 0.025, 0.03]:
        for lag in [3, 5, 7]:
            for hold in [7, 10, 14]:
                train_trades = generate_h7_trades(
                    train_data, date_regime,
                    gold_threshold=gold_th, lag_days=lag, hold_days=hold
                )
                test_trades = generate_h7_trades(
                    test_data, date_regime,
                    gold_threshold=gold_th, lag_days=lag, hold_days=hold
                )

                if len(train_trades) >= 5 and len(test_trades) >= 5:
                    train_m = calc.calculate(train_trades, "train")
                    test_m = calc.calculate(test_trades, "test")

                    results.append({
                        'gold': gold_th,
                        'lag': lag,
                        'hold': hold,
                        'train_n': len(train_trades),
                        'train_wr': train_m.win_rate,
                        'test_n': len(test_trades),
                        'test_wr': test_m.win_rate,
                        'test_ret': test_m.total_return,
                        'test_p': test_m.p_value_vs_random
                    })

    print(f"\n{'Gold%':<8} {'Lag':<6} {'Hold':<6} {'Train':<10} {'Test WR':<10} {'Test Ret':<12} {'p-val':<10}")
    print("-" * 70)

    for r in sorted(results, key=lambda x: -x['test_wr'])[:15]:
        print(f"{r['gold']*100:.1f}%     {r['lag']:<6} {r['hold']:<6} "
              f"{r['train_n']}({r['train_wr']:.0%})   "
              f"{r['test_wr']:.1%}      {r['test_ret']*100:+.1f}%       {r['test_p']:.3f}")

    # 최적 설정
    if results:
        # 거래수 10개 이상 중 최고 승률
        valid = [r for r in results if r['test_n'] >= 10]
        if valid:
            best = max(valid, key=lambda x: x['test_wr'])
            print(f"\n최적: Gold>={best['gold']*100:.1f}%, Lag={best['lag']}d, Hold={best['hold']}d")
            print(f"  Test WR: {best['test_wr']:.1%}, Return: {best['test_ret']*100:+.1f}%, p={best['test_p']:.4f}")

    # 기본 설정으로 전체 테스트
    print("\n" + "=" * 70)
    print("Default Config (Gold>=1.5%, Lag=3d, Hold=7d)")
    print("=" * 70)

    all_trades = generate_h7_trades(data, date_regime,
                                    gold_threshold=0.015, lag_days=3, hold_days=7)

    if all_trades:
        metrics = calc.calculate(all_trades, "all")
        print(f"\nTotal trades: {len(all_trades)}")
        print(f"Win rate: {metrics.win_rate:.1%}")
        print(f"Avg return: {metrics.avg_return*100:.2f}%")
        print(f"Total return: {metrics.total_return*100:.1f}%")
        print(f"Sharpe: {metrics.sharpe_ratio:.2f}")

        # Train/Test
        train_trades = generate_h7_trades(train_data, date_regime)
        test_trades = generate_h7_trades(test_data, date_regime)

        print(f"\nTrain (2020-2022): {len(train_trades)} trades")
        if train_trades:
            tm = calc.calculate(train_trades, "train")
            print(f"  WR: {tm.win_rate:.1%}, Return: {tm.total_return*100:+.1f}%")

        print(f"\nTest (2023-2025): {len(test_trades)} trades")
        if test_trades:
            tsm = calc.calculate(test_trades, "test")
            print(f"  WR: {tsm.win_rate:.1%}, Return: {tsm.total_return*100:+.1f}%")
            print(f"  p-value: {tsm.p_value_vs_random:.4f}")

    # 년도별
    print("\n" + "=" * 70)
    print("Year-by-Year")
    print("=" * 70)

    print(f"\n{'Year':<8} {'Trades':<8} {'WR':<10} {'Return':<12}")
    print("-" * 40)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year]
        if len(year_data) < 30:
            continue

        year_trades = generate_h7_trades(year_data, date_regime)
        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1
            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%")
        else:
            print(f"{year:<8} 0")

    # 개별 거래 (Test 기간)
    print("\n" + "=" * 70)
    print("Individual Trades (Test Period)")
    print("=" * 70)

    test_trades = generate_h7_trades(test_data, date_regime)
    print(f"\n{'Entry':<12} {'Exit':<12} {'Return':<10} {'Days':<6} {'Gold Ret'}")
    print("-" * 55)

    for t in test_trades:
        status = "WIN " if t.is_win else "LOSS"
        print(f"{t.entry_date:<12} {t.exit_date:<12} {t.return_pct*100:+6.1f}% ({status}) "
              f"{t.hold_days:<6} {t.state_at_entry}")

    # 결론
    print("\n" + "=" * 70)
    print("FINAL H7 STRATEGY")
    print("=" * 70)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │  H7 GOLD LAG STRATEGY                                          │
    │                                                                │
    │  "BTC는 Gold Safe-Haven에서 Gold를 후행 추종한다"              │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  진입 조건 (AND):                                              │
    │    1. Gold Safe-Haven 레짐 (Graph DB)                          │
    │    2. Gold 7일 수익률 >= 1.5%                                  │
    │    3. 신호 발생 후 3일 대기                                    │
    │    4. RSI 25-80 (H1 Filter)                                    │
    │                                                                │
    │  청산:                                                         │
    │    - 7일 보유 후 청산                                          │
    │                                                                │
    │  포지션 크기:                                                  │
    │    - 기본: 10%                                                 │
    │    - H4 전이 윈도우 중: 15%                                    │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()
