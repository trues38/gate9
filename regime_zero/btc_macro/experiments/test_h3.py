"""
H3: Volatility Expansion + First Dip Test

가설: 변동성이 급격히 확장된 이후, 첫 번째 조정(dip)은
      추세 재개 확률이 높다.

논리:
- 변동성 확장 = 레짐 전환 신호
- 첫 눌림 = "겁먹은 손절 + 기관 대기 물량" 구간

조건:
- 진입: 7일 변동성 Z-score >= 1.5 이후, RSI 40~50으로 되돌림
- 청산: RSI >= 65 OR 7일 보유 OR -5% 손절
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_volatility(prices: pd.Series, window: int = 7) -> pd.Series:
    """일간 수익률 기반 변동성 계산"""
    returns = prices.pct_change()
    volatility = returns.rolling(window=window).std() * np.sqrt(252)
    return volatility


def calculate_volatility_zscore(volatility: pd.Series, lookback: int = 60) -> pd.Series:
    """변동성 Z-score 계산"""
    mean = volatility.rolling(window=lookback, min_periods=20).mean()
    std = volatility.rolling(window=lookback, min_periods=20).std()
    zscore = (volatility - mean) / std
    return zscore


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

    # 변동성
    btc['Volatility'] = calculate_volatility(btc['Close'], window=7)

    # 변동성 Z-score
    btc['Vol_Zscore'] = calculate_volatility_zscore(btc['Volatility'])

    # 최근 N일 내 고변동성 발생 여부
    btc['Had_Vol_Spike_5d'] = btc['Vol_Zscore'].rolling(window=5).max() >= 1.5
    btc['Had_Vol_Spike_7d'] = btc['Vol_Zscore'].rolling(window=7).max() >= 1.5
    btc['Had_Vol_Spike_10d'] = btc['Vol_Zscore'].rolling(window=10).max() >= 1.5

    # RSI가 40-50 범위인지
    btc['RSI_In_Dip'] = (btc['RSI'] >= 40) & (btc['RSI'] <= 50)

    btc = btc.dropna()

    print(f"Loaded {len(btc)} days of data")
    return btc


def identify_vol_expansion_dip(data: pd.DataFrame,
                                vol_zscore_threshold: float = 1.5,
                                lookback_days: int = 7,
                                rsi_low: float = 40,
                                rsi_high: float = 50) -> pd.Series:
    """
    변동성 확장 후 눌림 구간 식별

    조건:
    1. 최근 lookback_days 내에 Vol Z-score >= threshold 발생
    2. 현재 RSI가 rsi_low ~ rsi_high (눌림 구간)
    3. 현재 Vol Z-score는 정상화됨 (< threshold)
    """
    # 최근 N일 내 변동성 스파이크 발생
    vol_spike_occurred = data['Vol_Zscore'].rolling(window=lookback_days).max() >= vol_zscore_threshold

    # 현재 RSI가 눌림 구간
    rsi_in_dip = (data['RSI'] >= rsi_low) & (data['RSI'] <= rsi_high)

    # 현재 변동성은 정상화 (스파이크 직후가 아님)
    vol_normalized = data['Vol_Zscore'] < vol_zscore_threshold

    # 모든 조건 충족
    signal = vol_spike_occurred & rsi_in_dip & vol_normalized

    return signal


def generate_h3_trades(data: pd.DataFrame,
                       vol_zscore: float = 1.5,
                       lookback: int = 7,
                       rsi_low: float = 40,
                       rsi_high: float = 50,
                       take_profit_rsi: float = 65,
                       max_hold_days: int = 7,
                       stop_loss: float = -0.05) -> List[TradeResult]:
    """
    H3 가설 기반 거래 생성

    진입: 변동성 확장 후 RSI 눌림
    청산: RSI >= take_profit_rsi OR hold_days >= max_hold_days OR return <= stop_loss
    """
    trades = []
    position = None

    # 진입 신호
    data = data.copy()
    data['Entry_Signal'] = identify_vol_expansion_dip(
        data, vol_zscore, lookback, rsi_low, rsi_high
    )

    for i in range(len(data)):
        row = data.iloc[i]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['Close']
        rsi = row['RSI']

        if position is None:
            # 진입 조건
            if row['Entry_Signal']:
                position = (date, price, i, rsi, row['Vol_Zscore'])
        else:
            entry_date, entry_price, entry_idx, entry_rsi, entry_vol_z = position
            hold_days = i - entry_idx
            return_pct = (price - entry_price) / entry_price

            # 청산 조건
            should_exit = False
            exit_reason = ""

            if rsi >= take_profit_rsi:
                should_exit = True
                exit_reason = "TP_RSI"
            elif hold_days >= max_hold_days:
                should_exit = True
                exit_reason = "MAX_HOLD"
            elif return_pct <= stop_loss:
                should_exit = True
                exit_reason = "STOP_LOSS"

            if should_exit:
                is_win = return_pct > 0

                trades.append(TradeResult(
                    entry_date=entry_date,
                    exit_date=date,
                    entry_price=entry_price,
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=is_win,
                    hold_days=hold_days,
                    state_at_entry=f"vol_z{entry_vol_z:.1f}|rsi{int(entry_rsi)}|{exit_reason}"
                ))
                position = None

    return trades


def analyze_vol_expansion_events(data: pd.DataFrame, threshold: float = 1.5):
    """변동성 확장 이벤트 분석"""
    print("\n=== 변동성 확장 이벤트 분석 ===")

    # Vol Z-score >= threshold 인 날들
    high_vol_days = data[data['Vol_Zscore'] >= threshold]

    print(f"\nVol Z-score >= {threshold} 발생일: {len(high_vol_days)} / {len(data)} ({len(high_vol_days)/len(data)*100:.1f}%)")

    # 년도별 분포
    print("\n년도별 고변동성 발생:")
    for year in range(2020, 2026):
        year_data = data[data.index.year == year]
        year_high_vol = year_data[year_data['Vol_Zscore'] >= threshold]
        if len(year_data) > 0:
            print(f"  {year}: {len(year_high_vol)} days ({len(year_high_vol)/len(year_data)*100:.1f}%)")

    # 고변동성 후 7일 수익률 분포
    print("\n고변동성 발생 후 7일 수익률:")
    forward_returns = []
    for idx in high_vol_days.index:
        pos = data.index.get_loc(idx)
        if pos + 7 < len(data):
            future_price = data.iloc[pos + 7]['Close']
            current_price = data.iloc[pos]['Close']
            ret = (future_price - current_price) / current_price
            forward_returns.append(ret)

    if forward_returns:
        print(f"  Mean: {np.mean(forward_returns)*100:+.2f}%")
        print(f"  Median: {np.median(forward_returns)*100:+.2f}%")
        print(f"  Win Rate: {sum(1 for r in forward_returns if r > 0)/len(forward_returns)*100:.1f}%")


def run_parameter_sweep(data: pd.DataFrame, train_end: str) -> List[Dict]:
    """파라미터 스윕"""
    calc = MetricsCalculator()

    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    results = []

    for vol_z in [1.0, 1.5, 2.0]:
        for lookback in [5, 7, 10]:
            for rsi_range in [(35, 45), (40, 50), (45, 55)]:
                # Train
                train_trades = generate_h3_trades(
                    train_data,
                    vol_zscore=vol_z,
                    lookback=lookback,
                    rsi_low=rsi_range[0],
                    rsi_high=rsi_range[1]
                )

                # Test
                test_trades = generate_h3_trades(
                    test_data,
                    vol_zscore=vol_z,
                    lookback=lookback,
                    rsi_low=rsi_range[0],
                    rsi_high=rsi_range[1]
                )

                if len(train_trades) >= 5 and len(test_trades) >= 5:
                    train_metrics = calc.calculate(train_trades, "train")
                    test_metrics = calc.calculate(test_trades, "test")

                    results.append({
                        'vol_zscore': vol_z,
                        'lookback': lookback,
                        'rsi_range': rsi_range,
                        'train_trades': len(train_trades),
                        'train_wr': train_metrics.win_rate,
                        'test_trades': len(test_trades),
                        'test_wr': test_metrics.win_rate,
                        'test_return': test_metrics.total_return,
                        'test_pval': test_metrics.p_value_vs_random,
                        'decay': train_metrics.win_rate - test_metrics.win_rate
                    })

    return results


def main():
    print("=" * 60)
    print("H3: Volatility Expansion + First Dip Test")
    print("=" * 60)

    # 1. 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")

    # 2. 변동성 확장 이벤트 분석
    analyze_vol_expansion_events(data, threshold=1.5)

    # 3. 기본 테스트
    print("\n" + "=" * 60)
    print("Basic Test: Vol Z-score >= 1.5 → RSI 40-50 Dip")
    print("=" * 60)

    trades = generate_h3_trades(data, vol_zscore=1.5, lookback=7, rsi_low=40, rsi_high=50)

    calc = MetricsCalculator()
    metrics = calc.calculate(trades, "all")

    print(f"\nTotal trades: {len(trades)}")
    print(f"Win rate: {metrics.win_rate:.1%}")
    print(f"Avg return: {metrics.avg_return*100:.2f}%")
    print(f"Total return: {metrics.total_return*100:.1f}%")
    print(f"Max drawdown: {metrics.max_drawdown:.1%}")
    print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"p-value: {metrics.p_value_vs_random:.4f}")

    # 개별 거래 출력
    print("\n개별 거래:")
    for t in trades[:10]:
        print(f"  {t.entry_date} → {t.exit_date}: {t.return_pct*100:+.1f}% ({'WIN' if t.is_win else 'LOSS'}) [{t.state_at_entry}]")
    if len(trades) > 10:
        print(f"  ... and {len(trades) - 10} more trades")

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

        year_trades = generate_h3_trades(year_data, vol_zscore=1.5, lookback=7, rsi_low=40, rsi_high=50)
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

    print(f"\nTrain: {train_data.index[0].strftime('%Y-%m-%d')} ~ {train_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"Test: {test_data.index[0].strftime('%Y-%m-%d')} ~ {test_data.index[-1].strftime('%Y-%m-%d')}")

    train_trades = generate_h3_trades(train_data, vol_zscore=1.5, lookback=7, rsi_low=40, rsi_high=50)
    test_trades = generate_h3_trades(test_data, vol_zscore=1.5, lookback=7, rsi_low=40, rsi_high=50)

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
        # OOS 승률 기준 정렬
        sweep_results.sort(key=lambda x: -x['test_wr'])

        print(f"\n{'Vol_Z':<8} {'Lookback':<10} {'RSI Range':<12} {'Train WR':<10} {'Test WR':<10} {'Test N':<8} {'p-val':<8}")
        print("-" * 75)

        for r in sweep_results[:15]:
            print(f"{r['vol_zscore']:<8} {r['lookback']:<10} {str(r['rsi_range']):<12} "
                  f"{r['train_wr']:.1%}      {r['test_wr']:.1%}      {r['test_trades']:<8} {r['test_pval']:.3f}")

        # Best
        best = sweep_results[0]
        print(f"\nBest: Vol_Z>={best['vol_zscore']}, lookback={best['lookback']}d, RSI {best['rsi_range']}")
        print(f"  Test WR: {best['test_wr']:.1%}, Trades: {best['test_trades']}, p-value: {best['test_pval']:.4f}")

    # 7. 비교: 변동성 확장 후 진입 vs 무조건 진입
    print("\n" + "=" * 60)
    print("Comparison: Vol Expansion Dip vs Random Entry")
    print("=" * 60)

    # 무조건 7일 보유 (비교 기준)
    random_returns = []
    for i in range(0, len(test_data) - 7, 7):
        ret = (test_data.iloc[i+7]['Close'] - test_data.iloc[i]['Close']) / test_data.iloc[i]['Close']
        random_returns.append(ret)

    random_wr = sum(1 for r in random_returns if r > 0) / len(random_returns)
    random_avg_ret = np.mean(random_returns)

    print(f"\nRandom 7d hold (baseline):")
    print(f"  Trades: {len(random_returns)}")
    print(f"  Win rate: {random_wr:.1%}")
    print(f"  Avg return: {random_avg_ret*100:.2f}%")

    print(f"\nH3 Vol Expansion Dip:")
    print(f"  Trades: {len(test_trades)}")
    print(f"  Win rate: {test_metrics.win_rate:.1%}")
    print(f"  Avg return: {test_metrics.avg_return*100:.2f}%")

    edge = test_metrics.win_rate - random_wr
    print(f"\nEdge vs random: {edge:+.1%}")

    # 8. 결론
    print("\n" + "=" * 60)
    print("Conclusion")
    print("=" * 60)

    checks = {
        'Test WR >= 55%': test_metrics.win_rate >= 0.55,
        'p-value <= 0.1': test_metrics.p_value_vs_random <= 0.1,
        'Decay < 15%': abs(decay) < 0.15,
        'Test trades >= 10': len(test_trades) >= 10,
        'Edge vs random >= 5%': edge >= 0.05
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    passed_count = sum(checks.values())
    print(f"\nPassed: {passed_count}/5")

    if passed_count >= 4:
        print("\nVerdict: VALIDATED - 변동성 확장 후 눌림 진입이 유효함")
    elif passed_count >= 3:
        print("\nVerdict: MARGINAL - 추가 검증 필요")
    else:
        print("\nVerdict: REJECTED - 가설 기각")


if __name__ == "__main__":
    main()
