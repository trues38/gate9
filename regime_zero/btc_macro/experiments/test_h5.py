"""
H5: RSI Velocity (dRSI) Test

가설: RSI 절대값(30, 70)은 약하지만
      RSI 변화 속도(dRSI)는 레짐 전환 힌트가 되는가?

진입: 3일간 RSI +8 이상 상승 AND RSI <= 55
청산: 3일간 RSI -8 이상 하락 OR 7일 보유
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from typing import List, Dict, Tuple

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_drsi(rsi: pd.Series, window: int = 3) -> pd.Series:
    """dRSI (RSI 변화량) 계산"""
    return rsi.diff(window)


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC 데이터 가져오기"""
    print(f"Fetching BTC data: {start_date} ~ {end_date}")
    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)

    if btc.empty:
        raise ValueError("Failed to fetch BTC data")

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)

    # RSI
    btc['RSI'] = calculate_rsi(btc['Close'])

    # dRSI (3일 변화량)
    btc['dRSI_3d'] = calculate_drsi(btc['RSI'], window=3)

    # 추가로 2일, 5일 변화량도 계산
    btc['dRSI_2d'] = calculate_drsi(btc['RSI'], window=2)
    btc['dRSI_5d'] = calculate_drsi(btc['RSI'], window=5)

    btc = btc.dropna()

    print(f"Loaded {len(btc)} days of data")
    return btc


def generate_drsi_trades(data: pd.DataFrame,
                         drsi_entry: float = 8,
                         drsi_exit: float = -8,
                         drsi_window: int = 3,
                         rsi_max: float = 55,
                         max_hold_days: int = 7) -> List[TradeResult]:
    """
    dRSI 기반 거래 생성

    진입: dRSI >= drsi_entry AND RSI <= rsi_max
    청산: dRSI <= drsi_exit OR hold_days >= max_hold_days
    """
    trades = []
    position = None

    drsi_col = f'dRSI_{drsi_window}d'

    for i in range(len(data)):
        row = data.iloc[i]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['Close']
        rsi = row['RSI']
        drsi = row[drsi_col]

        if position is None:
            # 진입 조건
            if drsi >= drsi_entry and rsi <= rsi_max:
                position = (date, price, i, rsi, drsi)
        else:
            entry_date, entry_price, entry_idx, entry_rsi, entry_drsi = position
            hold_days = i - entry_idx

            # 청산 조건
            should_exit = False
            if drsi <= drsi_exit:
                should_exit = True
            elif hold_days >= max_hold_days:
                should_exit = True

            if should_exit:
                return_pct = (price - entry_price) / entry_price
                is_win = return_pct > 0

                trades.append(TradeResult(
                    entry_date=entry_date,
                    exit_date=date,
                    entry_price=entry_price,
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=is_win,
                    hold_days=hold_days,
                    state_at_entry=f"rsi{int(entry_rsi)}|drsi{int(entry_drsi)}"
                ))
                position = None

    return trades


def run_parameter_sweep(data: pd.DataFrame, train_end: str) -> Dict:
    """파라미터 스윕"""
    calc = MetricsCalculator()

    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    results = []

    for drsi_threshold in [6, 8, 10, 12]:
        for drsi_window in [2, 3, 5]:
            for rsi_max in [50, 55, 60]:
                # Train
                train_trades = generate_drsi_trades(
                    train_data,
                    drsi_entry=drsi_threshold,
                    drsi_window=drsi_window,
                    rsi_max=rsi_max
                )

                # Test
                test_trades = generate_drsi_trades(
                    test_data,
                    drsi_entry=drsi_threshold,
                    drsi_window=drsi_window,
                    rsi_max=rsi_max
                )

                if len(train_trades) >= 5 and len(test_trades) >= 5:
                    train_metrics = calc.calculate(train_trades, "train")
                    test_metrics = calc.calculate(test_trades, "test")

                    results.append({
                        'drsi_threshold': drsi_threshold,
                        'drsi_window': drsi_window,
                        'rsi_max': rsi_max,
                        'train_trades': len(train_trades),
                        'train_wr': train_metrics.win_rate,
                        'train_return': train_metrics.total_return,
                        'test_trades': len(test_trades),
                        'test_wr': test_metrics.win_rate,
                        'test_return': test_metrics.total_return,
                        'decay': train_metrics.win_rate - test_metrics.win_rate
                    })

    return results


def analyze_drsi_distribution(data: pd.DataFrame):
    """dRSI 분포 분석"""
    print("\n=== dRSI 분포 분석 ===")

    drsi = data['dRSI_3d']

    print(f"\ndRSI 3d 통계:")
    print(f"  Mean: {drsi.mean():.2f}")
    print(f"  Std: {drsi.std():.2f}")
    print(f"  Min: {drsi.min():.2f}")
    print(f"  Max: {drsi.max():.2f}")

    # 분위수
    percentiles = [10, 25, 50, 75, 90]
    print(f"\n  Percentiles:")
    for p in percentiles:
        print(f"    {p}%: {np.percentile(drsi, p):.2f}")

    # dRSI +8 이상인 날
    high_drsi_days = (drsi >= 8).sum()
    print(f"\n  dRSI >= +8 days: {high_drsi_days} ({high_drsi_days/len(data)*100:.1f}%)")

    # dRSI -8 이하인 날
    low_drsi_days = (drsi <= -8).sum()
    print(f"  dRSI <= -8 days: {low_drsi_days} ({low_drsi_days/len(data)*100:.1f}%)")


def main():
    print("=" * 60)
    print("H5: RSI Velocity (dRSI) Test")
    print("=" * 60)

    # 1. 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")

    # 2. dRSI 분포 분석
    analyze_drsi_distribution(data)

    # 3. 기본 테스트 (dRSI >= 8, RSI <= 55)
    print("\n" + "=" * 60)
    print("Basic Test: dRSI >= 8, RSI <= 55")
    print("=" * 60)

    trades = generate_drsi_trades(data, drsi_entry=8, rsi_max=55)

    calc = MetricsCalculator()
    metrics = calc.calculate(trades, "all")

    print(f"\nTotal trades: {len(trades)}")
    print(f"Win rate: {metrics.win_rate:.1%}")
    print(f"Avg return: {metrics.avg_return*100:.2f}%")
    print(f"Total return: {metrics.total_return*100:.1f}%")
    print(f"Max drawdown: {metrics.max_drawdown:.1%}")
    print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"p-value vs random: {metrics.p_value_vs_random:.4f}")

    # 4. 년도별 분석
    print("\n" + "=" * 60)
    print("Year-by-Year Analysis")
    print("=" * 60)

    print(f"\n{'Year':<8} {'Trades':<8} {'Win Rate':<10} {'Return':<12}")
    print("-" * 40)

    for year in range(2020, 2026):
        year_data = data[data.index.year == year]
        if len(year_data) < 30:
            continue

        year_trades = generate_drsi_trades(year_data, drsi_entry=8, rsi_max=55)
        if year_trades:
            wr = sum(1 for t in year_trades if t.is_win) / len(year_trades)
            ret = np.prod([1 + t.return_pct for t in year_trades]) - 1
            print(f"{year:<8} {len(year_trades):<8} {wr:.1%}      {ret*100:+.1f}%")
        else:
            print(f"{year:<8} 0")

    # 5. Walk-Forward 검증
    print("\n" + "=" * 60)
    print("Walk-Forward Validation")
    print("=" * 60)

    train_end = "2022-12-31"
    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    train_trades = generate_drsi_trades(train_data, drsi_entry=8, rsi_max=55)
    test_trades = generate_drsi_trades(test_data, drsi_entry=8, rsi_max=55)

    train_metrics = calc.calculate(train_trades, "train", is_in_sample=True)
    test_metrics = calc.calculate(test_trades, "test", is_in_sample=False)

    print(f"\nTrain (2020-2022):")
    print(f"  Trades: {len(train_trades)}")
    print(f"  Win rate: {train_metrics.win_rate:.1%}")
    print(f"  Return: {train_metrics.total_return*100:+.1f}%")

    print(f"\nTest (2023-2025):")
    print(f"  Trades: {len(test_trades)}")
    print(f"  Win rate: {test_metrics.win_rate:.1%}")
    print(f"  Return: {test_metrics.total_return*100:+.1f}%")
    print(f"  p-value: {test_metrics.p_value_vs_random:.4f}")

    decay = train_metrics.win_rate - test_metrics.win_rate
    print(f"\nDecay: {decay:+.1%}")

    # 6. 파라미터 스윕
    print("\n" + "=" * 60)
    print("Parameter Sweep")
    print("=" * 60)

    sweep_results = run_parameter_sweep(data, train_end)

    if sweep_results:
        print(f"\n{'dRSI':<6} {'Window':<8} {'RSI Max':<8} {'Train WR':<10} {'Test WR':<10} {'Decay':<8} {'Test N':<8}")
        print("-" * 70)

        for r in sorted(sweep_results, key=lambda x: -x['test_wr']):
            print(f"{r['drsi_threshold']:<6} {r['drsi_window']:<8} {r['rsi_max']:<8} "
                  f"{r['train_wr']:.1%}      {r['test_wr']:.1%}      {r['decay']:+.1%}    {r['test_trades']}")

        # Best
        best = max(sweep_results, key=lambda x: x['test_wr'] if x['test_trades'] >= 10 else 0)
        print(f"\nBest: dRSI>={best['drsi_threshold']}, window={best['drsi_window']}d, RSI<={best['rsi_max']}")
        print(f"  Test WR: {best['test_wr']:.1%}, Trades: {best['test_trades']}")

    # 7. H2 (RSI absolute) vs H5 (dRSI) 비교
    print("\n" + "=" * 60)
    print("Comparison: RSI Absolute (H2) vs dRSI Velocity (H5)")
    print("=" * 60)

    # H2: RSI <= 30 진입
    from btc_engine.experiments.test_h2 import calculate_bollinger_bands, get_bb_position, generate_h2_trades

    btc_h2 = data.copy()
    btc_h2['BB_Upper'], btc_h2['BB_Middle'], btc_h2['BB_Lower'] = calculate_bollinger_bands(btc_h2['Close'])
    btc_h2['BB_Position'] = btc_h2.apply(lambda r: get_bb_position(r['Close'], r['BB_Upper'], r['BB_Middle'], r['BB_Lower']), axis=1)

    h2_test_data = btc_h2[btc_h2.index > train_end]
    h2_trades = generate_h2_trades(h2_test_data, rsi_entry=30)
    h2_metrics = calc.calculate(h2_trades, "h2_test")

    print(f"\nH2 (RSI <= 30):")
    print(f"  Test trades: {len(h2_trades)}")
    print(f"  Test WR: {h2_metrics.win_rate:.1%}")
    print(f"  p-value: {h2_metrics.p_value_vs_random:.4f}")

    print(f"\nH5 (dRSI >= 8):")
    print(f"  Test trades: {len(test_trades)}")
    print(f"  Test WR: {test_metrics.win_rate:.1%}")
    print(f"  p-value: {test_metrics.p_value_vs_random:.4f}")

    if test_metrics.win_rate > h2_metrics.win_rate:
        print(f"\n→ dRSI가 RSI absolute보다 {(test_metrics.win_rate - h2_metrics.win_rate)*100:.1f}%p 우수")
    else:
        print(f"\n→ RSI absolute가 dRSI보다 {(h2_metrics.win_rate - test_metrics.win_rate)*100:.1f}%p 우수")

    # 8. 결론
    print("\n" + "=" * 60)
    print("Conclusion")
    print("=" * 60)

    checks = {
        'Test WR >= 55%': test_metrics.win_rate >= 0.55,
        'p-value <= 0.1': test_metrics.p_value_vs_random <= 0.1,
        'Decay < 15%': abs(decay) < 0.15,
        'Test trades >= 20': len(test_trades) >= 20,
        'Better than H2': test_metrics.win_rate > h2_metrics.win_rate
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    passed_count = sum(checks.values())
    print(f"\nPassed: {passed_count}/5")

    if passed_count >= 4:
        print("\nVerdict: VALIDATED - dRSI 속도 기반 진입이 RSI 절대값보다 유효함")
    elif passed_count >= 3:
        print("\nVerdict: MARGINAL - 추가 검증 필요")
    else:
        print("\nVerdict: REJECTED - 가설 기각")


if __name__ == "__main__":
    main()
