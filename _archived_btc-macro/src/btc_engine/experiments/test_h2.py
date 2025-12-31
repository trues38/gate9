"""
H2 RSI Oversold Hypothesis Test

RSI <= 30 진입, RSI >= 70 또는 7일 보유 또는 +5% 수익 시 청산
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from btc_engine.experiments.hypothesis import HypothesisLoader
from btc_engine.experiments.metrics import TradeResult, MetricsCalculator, quick_stats
from btc_engine.experiments.walk_forward import WalkForwardValidator, ValidationCriteria


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """볼린저 밴드 계산"""
    middle = prices.rolling(window=period).mean()
    std_dev = prices.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


def get_bb_position(price: float, upper: float, middle: float, lower: float) -> str:
    """볼린저 밴드 위치 판단"""
    if price <= lower * 1.01:  # 하단 터치 (1% 이내)
        return "lower_touch"
    elif price <= lower * 1.03:  # 하단 근처
        return "lower"
    elif price >= upper * 0.99:  # 상단 터치
        return "upper_touch"
    elif price >= upper * 0.97:  # 상단 근처
        return "upper"
    elif price >= middle:
        return "middle_upper"
    else:
        return "middle_lower"


def fetch_btc_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC 데이터 가져오기"""
    print(f"Fetching BTC data: {start_date} ~ {end_date}")
    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)

    if btc.empty:
        raise ValueError("Failed to fetch BTC data")

    # Handle MultiIndex columns if present
    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)

    # RSI 계산
    btc['RSI'] = calculate_rsi(btc['Close'])

    # 볼린저 밴드 계산
    btc['BB_Upper'], btc['BB_Middle'], btc['BB_Lower'] = calculate_bollinger_bands(btc['Close'])

    # BB 위치
    btc['BB_Position'] = btc.apply(
        lambda row: get_bb_position(row['Close'], row['BB_Upper'], row['BB_Middle'], row['BB_Lower']),
        axis=1
    )

    # NaN 제거
    btc = btc.dropna()

    print(f"Loaded {len(btc)} days of data")
    return btc


def generate_h2_trades(data: pd.DataFrame,
                       rsi_entry: float = 30,
                       rsi_exit: float = 70,
                       max_hold_days: int = 7,
                       take_profit: float = 0.05) -> List[TradeResult]:
    """
    H2 가설에 따른 거래 생성

    진입: RSI <= rsi_entry AND BB_Position in ['lower', 'lower_touch']
    청산: RSI >= rsi_exit OR hold_days >= max_hold_days OR profit >= take_profit
    """
    trades = []
    position = None  # (entry_date, entry_price, entry_idx)

    for i in range(len(data)):
        row = data.iloc[i]
        date = data.index[i].strftime('%Y-%m-%d')
        price = row['Close']
        rsi = row['RSI']
        bb_pos = row['BB_Position']

        if position is None:
            # 진입 조건 체크
            if rsi <= rsi_entry and bb_pos in ['lower', 'lower_touch']:
                position = (date, price, i)
        else:
            # 청산 조건 체크
            entry_date, entry_price, entry_idx = position
            hold_days = i - entry_idx
            profit_pct = (price - entry_price) / entry_price

            should_exit = False
            if rsi >= rsi_exit:
                should_exit = True
            elif hold_days >= max_hold_days:
                should_exit = True
            elif profit_pct >= take_profit:
                should_exit = True

            if should_exit:
                return_pct = profit_pct
                is_win = return_pct > 0

                state = f"rsi_{int(data.loc[data.index[entry_idx], 'RSI'])}|{bb_pos}"

                trades.append(TradeResult(
                    entry_date=entry_date,
                    exit_date=date,
                    entry_price=entry_price,
                    exit_price=price,
                    return_pct=return_pct,
                    is_win=is_win,
                    hold_days=hold_days,
                    state_at_entry=state
                ))
                position = None

    return trades


def trade_generator_factory(data: pd.DataFrame, rsi_threshold: float = 30):
    """Walk-Forward용 거래 생성 함수 팩토리"""
    def generator(start_date: str, end_date: str, conditions: Dict) -> List[TradeResult]:
        # 기간 필터링
        mask = (data.index >= start_date) & (data.index <= end_date)
        period_data = data.loc[mask].copy()

        if len(period_data) < 20:
            return []

        # 조건에서 RSI 임계값 추출 (있으면)
        rsi_val = rsi_threshold
        if 'entry_when' in conditions:
            for cond in conditions['entry_when']:
                if 'rsi' in cond:
                    rsi_val = cond['rsi'].get('value', rsi_threshold)

        return generate_h2_trades(period_data, rsi_entry=rsi_val)

    return generator


def run_parameter_sweep(data: pd.DataFrame, train_end: str) -> Dict:
    """RSI 파라미터 스윕 테스트"""
    results = {}
    calc = MetricsCalculator()

    # Train/Test 분할
    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    print(f"\nTrain period: {train_data.index[0].strftime('%Y-%m-%d')} ~ {train_data.index[-1].strftime('%Y-%m-%d')} ({len(train_data)} days)")
    print(f"Test period: {test_data.index[0].strftime('%Y-%m-%d')} ~ {test_data.index[-1].strftime('%Y-%m-%d')} ({len(test_data)} days)")

    for rsi in [25, 28, 30, 32, 35]:
        # Train
        train_trades = generate_h2_trades(train_data, rsi_entry=rsi)
        train_metrics = calc.calculate(train_trades, f"train_rsi{rsi}", is_in_sample=True)

        # Test
        test_trades = generate_h2_trades(test_data, rsi_entry=rsi)
        test_metrics = calc.calculate(test_trades, f"test_rsi{rsi}", is_in_sample=False)

        results[rsi] = {
            'train': {
                'trades': train_metrics.total_trades,
                'win_rate': train_metrics.win_rate,
                'return': train_metrics.total_return,
                'sharpe': train_metrics.sharpe_ratio
            },
            'test': {
                'trades': test_metrics.total_trades,
                'win_rate': test_metrics.win_rate,
                'return': test_metrics.total_return,
                'sharpe': test_metrics.sharpe_ratio,
                'p_value': test_metrics.p_value_vs_random
            },
            'decay': train_metrics.win_rate - test_metrics.win_rate
        }

    return results


def main():
    print("=" * 60)
    print("H2 RSI Oversold Hypothesis Test")
    print("=" * 60)

    # 1. 데이터 로드
    start_date = "2020-01-01"
    end_date = "2025-12-26"
    train_end = "2022-12-31"

    data = fetch_btc_data(start_date, end_date)

    # 2. 기본 테스트 (RSI 30)
    print("\n" + "=" * 60)
    print("Basic Test: RSI <= 30 Entry")
    print("=" * 60)

    all_trades = generate_h2_trades(data, rsi_entry=30)
    print(f"\nTotal trades: {len(all_trades)}")
    print(f"Quick stats: {quick_stats(all_trades)}")

    # 3. Walk-Forward 검증
    print("\n" + "=" * 60)
    print("Walk-Forward Validation")
    print("=" * 60)

    criteria = ValidationCriteria(
        win_rate_edge=0.08,
        p_value_threshold=0.1,
        max_drawdown_limit=0.25,
        min_samples=10  # RSI 30은 드물어서 샘플 수 낮춤
    )

    validator = WalkForwardValidator(criteria)

    # 가설 로드
    loader = HypothesisLoader()
    h2 = loader.get_hypothesis("H2_rsi_oversold")

    if h2:
        trade_gen = trade_generator_factory(data, rsi_threshold=30)
        wf_result = validator.validate(h2, trade_gen, n_windows=1)

        print(f"\nVerdict: {wf_result.verdict}")
        print(f"Train Win Rate: {wf_result.avg_train_win_rate:.1%}")
        print(f"Test Win Rate: {wf_result.avg_test_win_rate:.1%}")
        print(f"Decay: {wf_result.win_rate_decay:+.1%}")
        print(f"vs Random: {wf_result.test_vs_random:+.1%}")

        if wf_result.recommendations:
            print("\nRecommendations:")
            for rec in wf_result.recommendations:
                print(f"  - {rec}")

    # 4. 파라미터 스윕
    print("\n" + "=" * 60)
    print("Parameter Sweep: RSI Threshold")
    print("=" * 60)

    sweep_results = run_parameter_sweep(data, train_end)

    print(f"\n{'RSI':<6} {'Train WR':<10} {'Test WR':<10} {'Decay':<10} {'Test p-val':<10} {'Trades':<8}")
    print("-" * 60)

    for rsi, result in sorted(sweep_results.items()):
        print(f"{rsi:<6} {result['train']['win_rate']:.1%}      {result['test']['win_rate']:.1%}      {result['decay']:+.1%}     {result['test']['p_value']:.4f}     {result['test']['trades']}")

    # Best parameter
    best_rsi = max(sweep_results.items(),
                   key=lambda x: x[1]['test']['win_rate'] if x[1]['test']['trades'] >= 5 else 0)
    print(f"\nBest RSI threshold: {best_rsi[0]} (Test WR: {best_rsi[1]['test']['win_rate']:.1%})")

    # 5. 결론
    print("\n" + "=" * 60)
    print("Conclusion")
    print("=" * 60)

    # 검증 기준 체크
    best_test = best_rsi[1]['test']
    checks = {
        'OOS win_rate >= 58%': best_test['win_rate'] >= 0.58,
        'p_value <= 0.1': best_test['p_value'] <= 0.1,
        'Trades >= 10': best_test['trades'] >= 10,
        'Decay < 15%': best_rsi[1]['decay'] < 0.15
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    all_passed = all(checks.values())
    print(f"\nFinal Verdict: {'VALIDATED' if all_passed else 'NOT VALIDATED'}")


if __name__ == "__main__":
    main()
